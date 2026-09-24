"""AISStream message parsing and subscription boxes."""

import json

from src.services.tracks.vessels import VesselUpdate, parse_message, subscription_boxes


def position(**overrides):
    body = {"UserID": 259000420, "Latitude": 35.4, "Longitude": 139.7, "Sog": 12.3, "Cog": 90.0,
            "TrueHeading": 88, "Valid": True}
    body.update(overrides)
    return json.dumps({
        "MessageType": "PositionReport",
        "MetaData": {"MMSI": body["UserID"], "ShipName": "PACIFIC RELIEF   "},
        "Message": {"PositionReport": body},
    })


def test_position_report():
    update = parse_message(position())
    assert update is not None
    assert (update.mmsi, update.latitude, update.longitude) == (259000420, 35.4, 139.7)
    assert (update.speed_kn, update.course_deg, update.heading_deg) == (12.3, 90.0, 88.0)
    assert update.name == "PACIFIC RELIEF"


def test_not_available_values_become_none():
    update = parse_message(position(TrueHeading=511, Cog=360, Sog=102.3))
    assert (update.heading_deg, update.course_deg, update.speed_kn) == (None, None, None)


def test_unusable_messages_are_dropped():
    assert parse_message(position(Latitude=91)) is None  # AIS "no position"
    assert parse_message(position(Valid=False)) is None
    assert parse_message(position(UserID=123)) is None  # not a 9-digit MMSI
    assert parse_message(b"not json") is None
    assert parse_message(json.dumps({"MessageType": "Interrogation", "Message": {}})) is None


def test_static_data_names_a_ship():
    raw = json.dumps({
        "MessageType": "ShipStaticData",
        "MetaData": {"MMSI": 440123456},
        "Message": {"ShipStaticData": {"UserID": 440123456, "Name": "SEWOL RESCUE", "Type": 52}},
    })
    update = parse_message(raw)
    assert (update.name, update.ship_type, update.latitude) == ("SEWOL RESCUE", 52, None)


def test_merge_keeps_known_fields():
    base = VesselUpdate(mmsi=440123456, latitude=1.0, longitude=2.0, name="A")
    merged = base.merge(VesselUpdate(mmsi=440123456, ship_type=52))
    assert (merged.latitude, merged.name, merged.ship_type) == (1.0, "A", 52)


def test_boxes_split_at_the_antimeridian():
    assert subscription_boxes([(35.0, 139.0)], 3, 10) == [[[32.0, 136.0], [38.0, 142.0]]]
    fiji = subscription_boxes([(-17.7, 178.5)], 3, 10)
    assert fiji == [[[-20.7, 175.5], [-14.7, 180.0]], [[-20.7, -180.0], [-14.7, -178.5]]]
    assert len(subscription_boxes([(0, 0)] * 30, 3, 20)) == 20
    polar = subscription_boxes([(89.0, 0.0)], 3, 10)[0]
    assert polar[1][0] == 90.0
