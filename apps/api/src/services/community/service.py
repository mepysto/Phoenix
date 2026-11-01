"""Business rules for organisations, needs, offers, connections and disclosures.

Who may do what:
- Anyone can read public needs, public offers and disclosures.
- Any signed-in user can apply for an organisation and post offers.
- Only members of an *approved* organisation can post needs or disclosures
  for it. Platform admins (PLATFORM_ADMIN_EMAILS) approve organisations.
- A connection needs both sides: a member of the need's organisation and the
  offer's author. Contact details are revealed to each side only then.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import Settings
from src.models.community import (
    Connect,
    ConnectStatus,
    Disclosure,
    MemberRole,
    Need,
    NeedStatus,
    NeedVisibility,
    Offer,
    OfferStatus,
    OfferVisibility,
    Org,
    OrgMembership,
    OrgStatus,
    User,
)
from src.models.event import Event
from src.schemas import community as s
from src.services.community.auth import is_platform_admin, normalize_email
from src.services.community.mailer import Mailer
from src.services.community.matching import NeedInput, OfferInput, rank_offers

MAX_PENDING_ORGS_PER_USER = 3
MATCH_CANDIDATES = 500


class CommunityError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFound(CommunityError):
    status_code = 404


class Forbidden(CommunityError):
    status_code = 403


class Conflict(CommunityError):
    status_code = 409


def _org_summary(org: Org) -> s.OrgSummary:
    return s.OrgSummary(
        id=org.id, name=org.name, org_type=org.org_type, status=org.status, website=org.website
    )


class Viewer:
    """The signed-in user (or nobody) with their organisation roles."""

    def __init__(self, user: User | None, roles: dict[UUID, tuple[Org, MemberRole]], admin: bool) -> None:
        self.user = user
        self.roles = roles
        self.admin = admin

    @property
    def id(self) -> UUID | None:
        return self.user.id if self.user else None

    def approved_org_ids(self) -> set[UUID]:
        return {oid for oid, (org, _) in self.roles.items() if org.status == OrgStatus.approved}

    def member_of_approved(self, org_id: UUID) -> bool:
        return org_id in self.approved_org_ids()

    def can_manage_org(self, org_id: UUID) -> bool:
        if self.admin:
            return True
        entry = self.roles.get(org_id)
        return bool(entry and entry[0].status == OrgStatus.approved and entry[1] == MemberRole.org_admin)


class CommunityService:
    def __init__(self, session: AsyncSession, settings: Settings, mailer: Mailer) -> None:
        self.session = session
        self.settings = settings
        self.mailer = mailer

    # --- viewer -------------------------------------------------------------

    async def viewer(self, user: User | None) -> Viewer:
        if user is None:
            return Viewer(None, {}, False)
        rows = (
            await self.session.execute(
                select(OrgMembership, Org)
                .join(Org, Org.id == OrgMembership.org_id)
                .where(OrgMembership.user_id == user.id)
            )
        ).all()
        roles = {org.id: (org, m.role) for m, org in rows}
        return Viewer(user, roles, is_platform_admin(user, self.settings))

    def me(self, viewer: Viewer) -> s.Me:
        assert viewer.user is not None
        return s.Me(
            id=viewer.user.id,
            email=viewer.user.email,
            display_name=viewer.user.display_name,
            is_platform_admin=viewer.admin,
            memberships=[
                s.Membership(org=_org_summary(org), role=role)
                for org, role in sorted(viewer.roles.values(), key=lambda x: x[0].name)
            ],
        )

    async def _user_by_email(self, email: str) -> User:
        address = normalize_email(email)
        user = await self.session.scalar(select(User).where(User.email == address))
        if user is None:
            user = User(email=address)
            self.session.add(user)
            await self.session.flush()
        return user

    # --- orgs ---------------------------------------------------------------

    async def apply_org(self, viewer: Viewer, data: s.OrgCreate) -> s.OrgSummary:
        assert viewer.user is not None
        pending = sum(1 for org, _ in viewer.roles.values() if org.status == OrgStatus.pending)
        if pending >= MAX_PENDING_ORGS_PER_USER:
            raise Conflict("You already have applications waiting for review")
        org = Org(
            name=data.name.strip(),
            org_type=data.org_type,
            primary_email=normalize_email(data.primary_email),
            website=data.website,
            requested_by_user_id=viewer.user.id,
        )
        self.session.add(org)
        await self.session.flush()
        self.session.add(OrgMembership(org_id=org.id, user_id=viewer.user.id, role=MemberRole.org_admin))
        await self.session.flush()
        for admin_email in self.settings.platform_admin_emails:
            await self.mailer.send(
                admin_email,
                f"Organisation waiting for review: {org.name}",
                f"{viewer.user.email} applied for {org.name} ({org.org_type.value}).\n"
                f"Review it at {self.settings.public_web_url.rstrip('/')}/connect/admin",
            )
        return _org_summary(org)

    async def list_orgs_for_review(self, viewer: Viewer, status: OrgStatus | None) -> list[s.OrgAdminView]:
        if not viewer.admin:
            raise Forbidden("Only platform admins can review organisations")
        q = (
            select(Org, User.email)
            .join(User, User.id == Org.requested_by_user_id)
            .order_by(Org.created_at.desc())
            .limit(200)
        )
        if status is not None:
            q = q.where(Org.status == status)
        return [
            s.OrgAdminView(
                **_org_summary(org).model_dump(),
                primary_email=org.primary_email,
                requested_by_email=email,
                created_at=org.created_at,
                rejection_reason=org.rejection_reason,
            )
            for org, email in (await self.session.execute(q)).all()
        ]

    async def decide_org(self, viewer: Viewer, org_id: UUID, approve: bool, reason: str | None) -> s.OrgSummary:
        if not viewer.admin or viewer.user is None:
            raise Forbidden("Only platform admins can review organisations")
        org = await self.session.get(Org, org_id)
        if org is None:
            raise NotFound("Organisation not found")
        org.status = OrgStatus.approved if approve else OrgStatus.rejected
        org.decided_by_user_id = viewer.user.id
        org.decided_at = datetime.now(UTC)
        org.rejection_reason = None if approve else reason
        requester = await self.session.get(User, org.requested_by_user_id)
        if requester is not None:
            if approve:
                body = f"{org.name} is approved. Members can now post needs on Phoenix."
            else:
                body = f"{org.name} was not approved." + (f"\n\nReason: {reason}" if reason else "")
            await self.mailer.send(requester.email, f"Phoenix: {org.name}", body)
        await self.session.flush()
        return _org_summary(org)

    async def add_member(self, viewer: Viewer, org_id: UUID, data: s.MemberAdd) -> s.Membership:
        if not viewer.can_manage_org(org_id):
            raise Forbidden("Only admins of an approved organisation can add members")
        org = await self.session.get(Org, org_id)
        if org is None:
            raise NotFound("Organisation not found")
        user = await self._user_by_email(data.email)
        membership = await self.session.get(OrgMembership, (org_id, user.id))
        if membership is None:
            membership = OrgMembership(org_id=org_id, user_id=user.id, role=data.role)
            self.session.add(membership)
        else:
            membership.role = data.role
        await self.session.flush()
        await self.mailer.send(
            user.email,
            f"You were added to {org.name} on Phoenix",
            f"Sign in at {self.settings.public_web_url.rstrip('/')}/login with this address to act for {org.name}.",
        )
        return s.Membership(org=_org_summary(org), role=membership.role)

    # --- needs --------------------------------------------------------------

    def _need_out(self, need: Need, viewer: Viewer) -> s.NeedOut:
        return s.NeedOut(
            id=need.id,
            event_id=need.event_id,
            org=_org_summary(need.org),
            contact_email=need.org.primary_email,
            title=need.title,
            description=need.description,
            categories=list(need.categories or []),
            priority=need.priority,
            quantity=need.quantity,
            unit=need.unit,
            beneficiaries=need.beneficiaries,
            latitude=need.latitude,
            longitude=need.longitude,
            place_name=need.place_name,
            status=need.status,
            visibility=need.visibility,
            created_at=need.created_at,
            updated_at=need.updated_at,
            can_edit=viewer.admin or viewer.member_of_approved(need.org_id),
        )

    def _visible_needs(self, viewer: Viewer):
        q = select(Need).join(Org, Org.id == Need.org_id).options(selectinload(Need.org))
        # Needs of organisations that lost approval disappear from public view
        q = q.where(Org.status == OrgStatus.approved)
        if not viewer.admin:
            q = q.where(
                or_(
                    Need.visibility == NeedVisibility.public,
                    Need.org_id.in_(list(viewer.approved_org_ids()) or [None]),
                )
            )
        return q

    async def list_needs(
        self,
        viewer: Viewer,
        *,
        event_id: UUID | None,
        org_id: UUID | None,
        category: str | None,
        status: NeedStatus | None,
        limit: int,
        offset: int,
    ) -> s.NeedList:
        q = self._visible_needs(viewer)
        if event_id:
            q = q.where(Need.event_id == event_id)
        if org_id:
            q = q.where(Need.org_id == org_id)
        if category:
            q = q.where(Need.categories.contains([category]))
        if status:
            q = q.where(Need.status == status)
        total = await self.session.scalar(select(func.count()).select_from(q.order_by(None).subquery()))
        rows = (
            await self.session.scalars(
                q.order_by(Need.status, Need.priority.desc(), Need.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()
        return s.NeedList(data=[self._need_out(n, viewer) for n in rows], total=total or 0)

    async def _get_need(self, viewer: Viewer, need_id: UUID) -> Need:
        need = await self.session.scalar(self._visible_needs(viewer).where(Need.id == need_id))
        if need is None:
            raise NotFound("Need not found")
        return need

    async def get_need(self, viewer: Viewer, need_id: UUID) -> s.NeedOut:
        return self._need_out(await self._get_need(viewer, need_id), viewer)

    async def _require_event(self, event_id: UUID | None) -> None:
        if event_id is not None and await self.session.get(Event, event_id) is None:
            raise NotFound("Event not found")

    async def create_need(self, viewer: Viewer, data: s.NeedCreate) -> s.NeedOut:
        assert viewer.user is not None
        if not viewer.member_of_approved(data.org_id):
            raise Forbidden("Only members of an approved organisation can post its needs")
        await self._require_event(data.event_id)
        need = Need(**data.model_dump(), created_by_user_id=viewer.user.id)
        self.session.add(need)
        await self.session.flush()
        await self.session.refresh(need, ["org"])
        return self._need_out(need, viewer)

    async def update_need(self, viewer: Viewer, need_id: UUID, data: s.NeedUpdate) -> s.NeedOut:
        need = await self._get_need(viewer, need_id)
        if not (viewer.admin or viewer.member_of_approved(need.org_id)):
            raise Forbidden("Only the organisation's members can change this need")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(need, key, value)
        await self.session.flush()
        await self.session.refresh(need)
        return self._need_out(need, viewer)

    # --- offers -------------------------------------------------------------

    def _offer_out(self, offer: Offer, viewer: Viewer) -> s.OfferOut:
        return s.OfferOut(
            id=offer.id,
            event_id=offer.event_id,
            title=offer.title,
            description=offer.description,
            offer_type=offer.offer_type,
            categories=list(offer.categories or []),
            quantity=offer.quantity,
            unit=offer.unit,
            latitude=offer.latitude,
            longitude=offer.longitude,
            place_name=offer.place_name,
            status=offer.status,
            visibility=offer.visibility,
            created_at=offer.created_at,
            is_mine=viewer.id is not None and offer.created_by_user_id == viewer.id,
        )

    def _visible_offers(self, viewer: Viewer):
        q = select(Offer)
        if not viewer.admin:
            cond = Offer.visibility == OfferVisibility.public
            if viewer.id is not None:
                cond = or_(cond, Offer.created_by_user_id == viewer.id)
            q = q.where(cond)
        return q

    async def list_offers(
        self,
        viewer: Viewer,
        *,
        event_id: UUID | None,
        category: str | None,
        mine: bool,
        status: OfferStatus | None,
        limit: int,
        offset: int,
    ) -> s.OfferList:
        q = self._visible_offers(viewer)
        if event_id:
            q = q.where(Offer.event_id == event_id)
        if category:
            q = q.where(Offer.categories.contains([category]))
        if mine:
            q = q.where(Offer.created_by_user_id == viewer.id)
        if status:
            q = q.where(Offer.status == status)
        total = await self.session.scalar(select(func.count()).select_from(q.order_by(None).subquery()))
        rows = (await self.session.scalars(q.order_by(Offer.created_at.desc()).limit(limit).offset(offset))).all()
        return s.OfferList(data=[self._offer_out(o, viewer) for o in rows], total=total or 0)

    async def _get_offer(self, viewer: Viewer, offer_id: UUID) -> Offer:
        offer = await self.session.scalar(self._visible_offers(viewer).where(Offer.id == offer_id))
        if offer is None:
            raise NotFound("Offer not found")
        return offer

    async def create_offer(self, viewer: Viewer, data: s.OfferCreate) -> s.OfferOut:
        assert viewer.user is not None
        await self._require_event(data.event_id)
        offer = Offer(**data.model_dump(), created_by_user_id=viewer.user.id)
        self.session.add(offer)
        await self.session.flush()
        await self.session.refresh(offer)
        return self._offer_out(offer, viewer)

    async def update_offer(self, viewer: Viewer, offer_id: UUID, data: s.OfferUpdate) -> s.OfferOut:
        offer = await self._get_offer(viewer, offer_id)
        if not (viewer.admin or offer.created_by_user_id == viewer.id):
            raise Forbidden("Only the author can change this offer")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(offer, key, value)
        await self.session.flush()
        await self.session.refresh(offer)
        return self._offer_out(offer, viewer)

    # --- matching -----------------------------------------------------------

    async def matches(self, viewer: Viewer, need_id: UUID, limit: int) -> s.MatchList:
        need = await self._get_need(viewer, need_id)
        offers = (
            await self.session.scalars(
                self._visible_offers(viewer)
                .where(Offer.status == OfferStatus.open)
                .order_by(Offer.created_at.desc())
                .limit(MATCH_CANDIDATES)
            )
        ).all()
        by_id = {o.id: o for o in offers}
        ranked = rank_offers(
            NeedInput(
                categories=frozenset(need.categories or []),
                event_id=need.event_id,
                lat=need.latitude,
                lng=need.longitude,
                quantity=need.quantity,
                unit=need.unit,
            ),
            [
                OfferInput(
                    id=o.id,
                    offer_type=o.offer_type.value,
                    categories=frozenset(o.categories or []),
                    event_id=o.event_id,
                    lat=o.latitude,
                    lng=o.longitude,
                    quantity=o.quantity,
                    unit=o.unit,
                )
                for o in offers
            ],
            limit=limit,
        )
        return s.MatchList(
            need_id=need.id,
            data=[
                s.MatchOut(
                    offer=self._offer_out(by_id[m.offer_id], viewer),
                    score=m.score,
                    reasons=list(m.reasons),
                    distance_km=m.distance_km,
                )
                for m in ranked
            ],
        )

    # --- connects -------------------------------------------------------------

    def _sides(self, viewer: Viewer, connect: Connect) -> list[str]:
        sides: list[str] = []
        if viewer.member_of_approved(connect.need.org_id):
            sides.append("need")
        if viewer.id is not None and connect.offer.created_by_user_id == viewer.id:
            sides.append("offer")
        return sides

    async def _connect_out(self, viewer: Viewer, connect: Connect) -> s.ConnectOut:
        sides = self._sides(viewer, connect)
        counterpart: str | None = None
        if connect.status == ConnectStatus.approved:
            if "need" in sides and "offer" not in sides:
                author = await self.session.get(User, connect.offer.created_by_user_id)
                counterpart = author.email if author else None
            elif "offer" in sides and "need" not in sides:
                counterpart = connect.need.org.primary_email
        return s.ConnectOut(
            id=connect.id,
            need=self._need_out(connect.need, viewer),
            offer=self._offer_out(connect.offer, viewer),
            status=connect.status,
            message=connect.message,
            need_approved=connect.need_approved_at is not None,
            offer_approved=connect.offer_approved_at is not None,
            my_sides=sides,  # type: ignore[arg-type]
            counterpart_email=counterpart,
            created_at=connect.created_at,
            approved_at=connect.approved_at,
        )

    def _connect_query(self):
        return select(Connect).options(
            selectinload(Connect.need).selectinload(Need.org), selectinload(Connect.offer)
        )

    async def _get_connect(self, viewer: Viewer, connect_id: UUID) -> Connect:
        connect = await self.session.scalar(self._connect_query().where(Connect.id == connect_id))
        if connect is None or not (viewer.admin or self._sides(viewer, connect)):
            raise NotFound("Connection not found")
        return connect

    async def create_connect(self, viewer: Viewer, data: s.ConnectCreate) -> s.ConnectOut:
        assert viewer.user is not None
        need = await self._get_need(viewer, data.need_id)
        offer = await self._get_offer(viewer, data.offer_id)
        if need.status != NeedStatus.open or offer.status != OfferStatus.open:
            raise Conflict("Both the need and the offer must be open")
        on_need_side = viewer.member_of_approved(need.org_id)
        on_offer_side = offer.created_by_user_id == viewer.id
        if not (on_need_side or on_offer_side):
            raise Forbidden("Only the need's organisation or the offer's author can propose a connection")
        if on_need_side and on_offer_side:
            raise CommunityError("You cannot connect your own offer to your own need")
        now = datetime.now(UTC)
        connect = Connect(
            need_id=need.id,
            offer_id=offer.id,
            message=data.message,
            created_by_user_id=viewer.user.id,
            need_approved_by_user_id=viewer.user.id if on_need_side else None,
            need_approved_at=now if on_need_side else None,
            offer_approved_by_user_id=viewer.user.id if on_offer_side else None,
            offer_approved_at=now if on_offer_side else None,
        )
        self.session.add(connect)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise Conflict("This need and offer are already connected") from exc

        # Tell the other side, without revealing who is asking
        base = self.settings.public_web_url.rstrip("/")
        if on_need_side:
            author = await self.session.get(User, offer.created_by_user_id)
            if author is not None:
                await self.mailer.send(
                    author.email,
                    "An organisation would like your help",
                    f"{need.org.name} asks to connect your offer \"{offer.title}\" with their need "
                    f"\"{need.title}\".\nReview it at {base}/connect/mine",
                )
        else:
            await self.mailer.send(
                need.org.primary_email,
                "Someone offers help for your need",
                f"An offer \"{offer.title}\" was proposed for \"{need.title}\".\nReview it at {base}/connect/mine",
            )
        connect = await self._get_connect(viewer, connect.id)
        return await self._connect_out(viewer, connect)

    async def approve_connect(self, viewer: Viewer, connect_id: UUID) -> s.ConnectOut:
        assert viewer.user is not None
        connect = await self._get_connect(viewer, connect_id)
        if connect.status != ConnectStatus.pending:
            raise Conflict("This connection is no longer pending")
        sides = self._sides(viewer, connect)
        now = datetime.now(UTC)
        if "need" in sides and connect.need_approved_at is None:
            connect.need_approved_at = now
            connect.need_approved_by_user_id = viewer.user.id
        if "offer" in sides and connect.offer_approved_at is None:
            connect.offer_approved_at = now
            connect.offer_approved_by_user_id = viewer.user.id
        if connect.need_approved_at and connect.offer_approved_at:
            connect.status = ConnectStatus.approved
            connect.approved_at = now
            author = await self.session.get(User, connect.offer.created_by_user_id)
            org_email = connect.need.org.primary_email
            if author is not None:
                await self.mailer.send(
                    author.email,
                    "Connection approved",
                    f"\"{connect.offer.title}\" is connected with \"{connect.need.title}\" "
                    f"({connect.need.org.name}). Contact them at {org_email}.",
                )
                await self.mailer.send(
                    org_email,
                    "Connection approved",
                    f"\"{connect.need.title}\" is connected with the offer \"{connect.offer.title}\". "
                    f"Contact the offer's author at {author.email}.",
                )
        await self.session.flush()
        return await self._connect_out(viewer, connect)

    async def decline_connect(self, viewer: Viewer, connect_id: UUID) -> s.ConnectOut:
        assert viewer.user is not None
        connect = await self._get_connect(viewer, connect_id)
        if connect.status != ConnectStatus.pending:
            raise Conflict("This connection is no longer pending")
        connect.status = (
            ConnectStatus.canceled if connect.created_by_user_id == viewer.user.id else ConnectStatus.rejected
        )
        connect.closed_by_user_id = viewer.user.id
        connect.closed_at = datetime.now(UTC)
        await self.session.flush()
        return await self._connect_out(viewer, connect)

    async def my_connects(self, viewer: Viewer) -> s.ConnectList:
        assert viewer.user is not None
        q = (
            self._connect_query()
            .join(Need, Need.id == Connect.need_id)
            .join(Offer, Offer.id == Connect.offer_id)
            .where(
                or_(
                    Need.org_id.in_(list(viewer.approved_org_ids()) or [None]),
                    Offer.created_by_user_id == viewer.user.id,
                )
            )
            .order_by(Connect.created_at.desc())
            .limit(200)
        )
        rows = (await self.session.scalars(q)).all()
        return s.ConnectList(data=[await self._connect_out(viewer, c) for c in rows])

    # --- disclosures --------------------------------------------------------

    async def list_disclosures(self, event_id: UUID) -> s.DisclosureList:
        rows = (
            await self.session.scalars(
                select(Disclosure)
                .join(Org, Org.id == Disclosure.org_id)
                .where(Disclosure.event_id == event_id, Org.status == OrgStatus.approved)
                .options(selectinload(Disclosure.org))
                .order_by(Disclosure.created_at.desc())
                .limit(100)
            )
        ).all()
        return s.DisclosureList(
            data=[
                s.DisclosureOut(
                    id=d.id,
                    event_id=d.event_id,
                    org=_org_summary(d.org),
                    title=d.title,
                    body=d.body,
                    created_at=d.created_at,
                )
                for d in rows
            ]
        )

    async def create_disclosure(self, viewer: Viewer, event_id: UUID, data: s.DisclosureCreate) -> s.DisclosureOut:
        assert viewer.user is not None
        if not viewer.member_of_approved(data.org_id):
            raise Forbidden("Only members of an approved organisation can publish for it")
        await self._require_event(event_id)
        d = Disclosure(
            event_id=event_id,
            org_id=data.org_id,
            title=data.title,
            body=data.body,
            created_by_user_id=viewer.user.id,
        )
        self.session.add(d)
        await self.session.flush()
        await self.session.refresh(d, ["org"])
        return s.DisclosureOut(
            id=d.id, event_id=d.event_id, org=_org_summary(d.org), title=d.title, body=d.body, created_at=d.created_at
        )
