import type { Language } from "@/store/settingsStore";

export interface Translations {
  common: {
    home: string;
    events: string;
    about: string;
    settings: string;
    search: string;
    searchPlaceholder: string;
    backToMap: string;
    loading: string;
    error: string;
    retry: string;
    viewOnMap: string;
  };
  settings: {
    title: string;
    subtitle: string;
    language: string;
    languageDesc: string;
    displayLanguage: string;
    appearance: string;
    appearanceDesc: string;
    theme: string;
    enableAnimations: string;
    animationsDesc: string;
    mapPreferences: string;
    mapPreferencesDesc: string;
    defaultBasemap: string;
    defaultView: string;
    showClusterMarkers: string;
    clusterMarkersDesc: string;
    dataSync: string;
    dataSyncDesc: string;
    autoRefresh: string;
    autoRefreshDesc: string;
    refreshInterval: string;
    resetToDefaults: string;
    changesApplied: string;
    autoSaved: string;
  };
  about: {
    tagline: string;
    description: string;
    keyFeatures: string;
    dataSources: string;
    techStack: string;
    openSource: string;
    openSourceDesc: string;
    viewOnGithub: string;
    footer: string;
  };
  events: {
    title: string;
    eventsFound: string;
    noEvents: string;
    adjustFilters: string;
    clearFilters: string;
    affected: string;
    active: string;
    location: string;
    severity: string;
  };
  map: {
    globe3d: string;
    view2d: string;
    satellite: string;
    dark: string;
    activeEvents: string;
    initializingGlobe: string;
  };
}

const en: Translations = {
  common: {
    home: "Home",
    events: "Events",
    about: "About",
    settings: "Settings",
    search: "Search",
    searchPlaceholder: "Search events, locations...",
    backToMap: "Back to Map",
    loading: "Loading...",
    error: "Error",
    retry: "Retry",
    viewOnMap: "View on Map",
  },
  settings: {
    title: "Settings",
    subtitle: "Customize your Phoenix experience",
    language: "Language & Region",
    languageDesc: "Set your preferred language for the interface",
    displayLanguage: "Display Language",
    appearance: "Appearance",
    appearanceDesc: "Customize the visual appearance of the app",
    theme: "Theme",
    enableAnimations: "Enable Animations",
    animationsDesc: "Smooth transitions and visual effects",
    mapPreferences: "Map Preferences",
    mapPreferencesDesc: "Configure default map display settings",
    defaultBasemap: "Default Basemap",
    defaultView: "Default View",
    showClusterMarkers: "Show Cluster Markers",
    clusterMarkersDesc: "Group nearby events into clusters",
    dataSync: "Data & Sync",
    dataSyncDesc: "Control how data is fetched and updated",
    autoRefresh: "Auto-refresh Data",
    autoRefreshDesc: "Automatically fetch new events",
    refreshInterval: "Refresh Interval",
    resetToDefaults: "Reset to Defaults",
    changesApplied: "Changes are applied immediately.",
    autoSaved: "Settings are automatically saved to your browser.",
  },
  about: {
    tagline: "Digital twin platform where everyone can heal the wounds of the earth together",
    description: "Phoenix is a global open humanitarian platform that visualizes worldwide disasters, wars, and environmental pollution in real-time 3D digital twin, allowing anyone to participate in recovery planning.",
    keyFeatures: "Key Features",
    dataSources: "Data Sources",
    techStack: "Tech Stack",
    openSource: "Open Source",
    openSourceDesc: "Phoenix is open source and available under the MIT License. Contributions are welcome!",
    viewOnGithub: "View on GitHub",
    footer: "Built with care for humanitarian response and disaster recovery.",
  },
  events: {
    title: "Disaster Events",
    eventsFound: "events found",
    noEvents: "No events found",
    adjustFilters: "Try adjusting your filters",
    clearFilters: "Clear Filters",
    affected: "affected",
    active: "Active",
    location: "Location",
    severity: "Severity",
  },
  map: {
    globe3d: "3D Globe",
    view2d: "2D View",
    satellite: "Satellite",
    dark: "Dark",
    activeEvents: "Active Events",
    initializingGlobe: "Initializing Globe...",
  },
};

const ko: Translations = {
  common: {
    home: "홈",
    events: "이벤트",
    about: "소개",
    settings: "설정",
    search: "검색",
    searchPlaceholder: "이벤트, 위치 검색...",
    backToMap: "지도로 돌아가기",
    loading: "로딩 중...",
    error: "오류",
    retry: "다시 시도",
    viewOnMap: "지도에서 보기",
  },
  settings: {
    title: "설정",
    subtitle: "Phoenix 사용 환경을 맞춤 설정하세요",
    language: "언어 및 지역",
    languageDesc: "인터페이스에 사용할 언어를 선택하세요",
    displayLanguage: "표시 언어",
    appearance: "외관",
    appearanceDesc: "앱의 시각적 모양을 맞춤 설정하세요",
    theme: "테마",
    enableAnimations: "애니메이션 활성화",
    animationsDesc: "부드러운 전환 및 시각 효과",
    mapPreferences: "지도 설정",
    mapPreferencesDesc: "기본 지도 표시 설정을 구성하세요",
    defaultBasemap: "기본 베이스맵",
    defaultView: "기본 보기",
    showClusterMarkers: "클러스터 마커 표시",
    clusterMarkersDesc: "근처 이벤트를 클러스터로 그룹화",
    dataSync: "데이터 및 동기화",
    dataSyncDesc: "데이터를 가져오고 업데이트하는 방법을 제어하세요",
    autoRefresh: "자동 새로고침",
    autoRefreshDesc: "새 이벤트를 자동으로 가져오기",
    refreshInterval: "새로고침 간격",
    resetToDefaults: "기본값으로 재설정",
    changesApplied: "변경사항이 즉시 적용됩니다.",
    autoSaved: "설정이 브라우저에 자동 저장됩니다.",
  },
  about: {
    tagline: "모두가 함께 지구의 상처를 치유하는 디지털 트윈 플랫폼",
    description: "Phoenix는 전 세계의 재난, 전쟁, 환경오염 현황을 실시간 3D 디지털트윈으로 시각화하고, 누구나 복구 설계에 참여할 수 있는 글로벌 오픈 휴머니타리안 플랫폼입니다.",
    keyFeatures: "주요 기능",
    dataSources: "데이터 소스",
    techStack: "기술 스택",
    openSource: "오픈 소스",
    openSourceDesc: "Phoenix는 MIT 라이선스 하에 오픈 소스로 제공됩니다. 기여를 환영합니다!",
    viewOnGithub: "GitHub에서 보기",
    footer: "인도주의적 대응과 재난 복구를 위해 정성껏 만들었습니다.",
  },
  events: {
    title: "재난 이벤트",
    eventsFound: "개 이벤트 발견",
    noEvents: "이벤트를 찾을 수 없습니다",
    adjustFilters: "필터를 조정해 보세요",
    clearFilters: "필터 초기화",
    affected: "영향받은 인구",
    active: "진행 중",
    location: "위치",
    severity: "심각도",
  },
  map: {
    globe3d: "3D 지구본",
    view2d: "2D 보기",
    satellite: "위성",
    dark: "다크",
    activeEvents: "활성 이벤트",
    initializingGlobe: "지구본 초기화 중...",
  },
};

const es: Translations = {
  common: {
    home: "Inicio",
    events: "Eventos",
    about: "Acerca de",
    settings: "Configuración",
    search: "Buscar",
    searchPlaceholder: "Buscar eventos, ubicaciones...",
    backToMap: "Volver al mapa",
    loading: "Cargando...",
    error: "Error",
    retry: "Reintentar",
    viewOnMap: "Ver en el mapa",
  },
  settings: {
    title: "Configuración",
    subtitle: "Personaliza tu experiencia en Phoenix",
    language: "Idioma y región",
    languageDesc: "Establece tu idioma preferido para la interfaz",
    displayLanguage: "Idioma de visualización",
    appearance: "Apariencia",
    appearanceDesc: "Personaliza la apariencia visual de la aplicación",
    theme: "Tema",
    enableAnimations: "Habilitar animaciones",
    animationsDesc: "Transiciones suaves y efectos visuales",
    mapPreferences: "Preferencias del mapa",
    mapPreferencesDesc: "Configura los ajustes de visualización del mapa",
    defaultBasemap: "Mapa base predeterminado",
    defaultView: "Vista predeterminada",
    showClusterMarkers: "Mostrar marcadores agrupados",
    clusterMarkersDesc: "Agrupar eventos cercanos en clústeres",
    dataSync: "Datos y sincronización",
    dataSyncDesc: "Controla cómo se obtienen y actualizan los datos",
    autoRefresh: "Actualización automática",
    autoRefreshDesc: "Obtener nuevos eventos automáticamente",
    refreshInterval: "Intervalo de actualización",
    resetToDefaults: "Restablecer valores predeterminados",
    changesApplied: "Los cambios se aplican inmediatamente.",
    autoSaved: "La configuración se guarda automáticamente en tu navegador.",
  },
  about: {
    tagline: "Plataforma de gemelo digital donde todos pueden sanar las heridas de la tierra juntos",
    description: "Phoenix es una plataforma humanitaria global abierta que visualiza desastres mundiales, guerras y contaminación ambiental en tiempo real mediante un gemelo digital 3D.",
    keyFeatures: "Características principales",
    dataSources: "Fuentes de datos",
    techStack: "Stack tecnológico",
    openSource: "Código abierto",
    openSourceDesc: "Phoenix es de código abierto bajo la licencia MIT. ¡Las contribuciones son bienvenidas!",
    viewOnGithub: "Ver en GitHub",
    footer: "Construido con cuidado para la respuesta humanitaria y la recuperación ante desastres.",
  },
  events: {
    title: "Eventos de desastres",
    eventsFound: "eventos encontrados",
    noEvents: "No se encontraron eventos",
    adjustFilters: "Intenta ajustar tus filtros",
    clearFilters: "Limpiar filtros",
    affected: "afectados",
    active: "Activo",
    location: "Ubicación",
    severity: "Gravedad",
  },
  map: {
    globe3d: "Globo 3D",
    view2d: "Vista 2D",
    satellite: "Satélite",
    dark: "Oscuro",
    activeEvents: "Eventos activos",
    initializingGlobe: "Inicializando globo...",
  },
};

const fr: Translations = {
  common: {
    home: "Accueil",
    events: "Événements",
    about: "À propos",
    settings: "Paramètres",
    search: "Rechercher",
    searchPlaceholder: "Rechercher événements, lieux...",
    backToMap: "Retour à la carte",
    loading: "Chargement...",
    error: "Erreur",
    retry: "Réessayer",
    viewOnMap: "Voir sur la carte",
  },
  settings: {
    title: "Paramètres",
    subtitle: "Personnalisez votre expérience Phoenix",
    language: "Langue et région",
    languageDesc: "Définissez votre langue préférée pour l'interface",
    displayLanguage: "Langue d'affichage",
    appearance: "Apparence",
    appearanceDesc: "Personnalisez l'apparence visuelle de l'application",
    theme: "Thème",
    enableAnimations: "Activer les animations",
    animationsDesc: "Transitions fluides et effets visuels",
    mapPreferences: "Préférences de carte",
    mapPreferencesDesc: "Configurez les paramètres d'affichage de la carte",
    defaultBasemap: "Fond de carte par défaut",
    defaultView: "Vue par défaut",
    showClusterMarkers: "Afficher les marqueurs groupés",
    clusterMarkersDesc: "Regrouper les événements proches en clusters",
    dataSync: "Données et synchronisation",
    dataSyncDesc: "Contrôlez comment les données sont récupérées et mises à jour",
    autoRefresh: "Actualisation automatique",
    autoRefreshDesc: "Récupérer automatiquement les nouveaux événements",
    refreshInterval: "Intervalle d'actualisation",
    resetToDefaults: "Réinitialiser par défaut",
    changesApplied: "Les modifications sont appliquées immédiatement.",
    autoSaved: "Les paramètres sont automatiquement enregistrés dans votre navigateur.",
  },
  about: {
    tagline: "Plateforme de jumeau numérique où chacun peut guérir les blessures de la terre ensemble",
    description: "Phoenix est une plateforme humanitaire mondiale ouverte qui visualise les catastrophes, guerres et pollutions environnementales en temps réel via un jumeau numérique 3D.",
    keyFeatures: "Fonctionnalités clés",
    dataSources: "Sources de données",
    techStack: "Stack technique",
    openSource: "Open Source",
    openSourceDesc: "Phoenix est open source sous licence MIT. Les contributions sont les bienvenues !",
    viewOnGithub: "Voir sur GitHub",
    footer: "Construit avec soin pour la réponse humanitaire et la récupération après sinistre.",
  },
  events: {
    title: "Événements de catastrophe",
    eventsFound: "événements trouvés",
    noEvents: "Aucun événement trouvé",
    adjustFilters: "Essayez d'ajuster vos filtres",
    clearFilters: "Effacer les filtres",
    affected: "affectés",
    active: "Actif",
    location: "Emplacement",
    severity: "Gravité",
  },
  map: {
    globe3d: "Globe 3D",
    view2d: "Vue 2D",
    satellite: "Satellite",
    dark: "Sombre",
    activeEvents: "Événements actifs",
    initializingGlobe: "Initialisation du globe...",
  },
};

const zh: Translations = {
  common: {
    home: "首页",
    events: "事件",
    about: "关于",
    settings: "设置",
    search: "搜索",
    searchPlaceholder: "搜索事件、位置...",
    backToMap: "返回地图",
    loading: "加载中...",
    error: "错误",
    retry: "重试",
    viewOnMap: "在地图上查看",
  },
  settings: {
    title: "设置",
    subtitle: "自定义您的 Phoenix 体验",
    language: "语言和地区",
    languageDesc: "设置界面的首选语言",
    displayLanguage: "显示语言",
    appearance: "外观",
    appearanceDesc: "自定义应用程序的视觉外观",
    theme: "主题",
    enableAnimations: "启用动画",
    animationsDesc: "平滑过渡和视觉效果",
    mapPreferences: "地图偏好",
    mapPreferencesDesc: "配置默认地图显示设置",
    defaultBasemap: "默认底图",
    defaultView: "默认视图",
    showClusterMarkers: "显示聚类标记",
    clusterMarkersDesc: "将附近的事件分组到聚类中",
    dataSync: "数据与同步",
    dataSyncDesc: "控制数据的获取和更新方式",
    autoRefresh: "自动刷新",
    autoRefreshDesc: "自动获取新事件",
    refreshInterval: "刷新间隔",
    resetToDefaults: "重置为默认值",
    changesApplied: "更改立即生效。",
    autoSaved: "设置自动保存到浏览器。",
  },
  about: {
    tagline: "让每个人都能一起治愈地球伤痕的数字孪生平台",
    description: "Phoenix 是一个全球开放的人道主义平台，通过实时 3D 数字孪生可视化全球灾害、战争和环境污染，让任何人都能参与恢复规划。",
    keyFeatures: "主要功能",
    dataSources: "数据来源",
    techStack: "技术栈",
    openSource: "开源",
    openSourceDesc: "Phoenix 是 MIT 许可下的开源项目。欢迎贡献！",
    viewOnGithub: "在 GitHub 上查看",
    footer: "为人道主义响应和灾害恢复精心打造。",
  },
  events: {
    title: "灾害事件",
    eventsFound: "个事件",
    noEvents: "未找到事件",
    adjustFilters: "尝试调整筛选条件",
    clearFilters: "清除筛选",
    affected: "受影响",
    active: "进行中",
    location: "位置",
    severity: "严重程度",
  },
  map: {
    globe3d: "3D 地球",
    view2d: "2D 视图",
    satellite: "卫星",
    dark: "暗色",
    activeEvents: "活动事件",
    initializingGlobe: "正在初始化地球...",
  },
};

const ar: Translations = {
  common: {
    home: "الرئيسية",
    events: "الأحداث",
    about: "حول",
    settings: "الإعدادات",
    search: "بحث",
    searchPlaceholder: "البحث عن الأحداث والمواقع...",
    backToMap: "العودة إلى الخريطة",
    loading: "جاري التحميل...",
    error: "خطأ",
    retry: "إعادة المحاولة",
    viewOnMap: "عرض على الخريطة",
  },
  settings: {
    title: "الإعدادات",
    subtitle: "تخصيص تجربة Phoenix الخاصة بك",
    language: "اللغة والمنطقة",
    languageDesc: "تعيين لغتك المفضلة للواجهة",
    displayLanguage: "لغة العرض",
    appearance: "المظهر",
    appearanceDesc: "تخصيص المظهر المرئي للتطبيق",
    theme: "السمة",
    enableAnimations: "تمكين الرسوم المتحركة",
    animationsDesc: "انتقالات سلسة وتأثيرات بصرية",
    mapPreferences: "تفضيلات الخريطة",
    mapPreferencesDesc: "تكوين إعدادات عرض الخريطة الافتراضية",
    defaultBasemap: "خريطة الأساس الافتراضية",
    defaultView: "العرض الافتراضي",
    showClusterMarkers: "إظهار علامات التجمع",
    clusterMarkersDesc: "تجميع الأحداث القريبة في مجموعات",
    dataSync: "البيانات والمزامنة",
    dataSyncDesc: "التحكم في كيفية جلب البيانات وتحديثها",
    autoRefresh: "التحديث التلقائي",
    autoRefreshDesc: "جلب الأحداث الجديدة تلقائيًا",
    refreshInterval: "فترة التحديث",
    resetToDefaults: "إعادة التعيين إلى الافتراضي",
    changesApplied: "يتم تطبيق التغييرات فورًا.",
    autoSaved: "يتم حفظ الإعدادات تلقائيًا في متصفحك.",
  },
  about: {
    tagline: "منصة التوأم الرقمي حيث يمكن للجميع معالجة جراح الأرض معًا",
    description: "Phoenix هي منصة إنسانية عالمية مفتوحة تعرض الكوارث والحروب والتلوث البيئي في جميع أنحاء العالم في الوقت الفعلي عبر التوأم الرقمي ثلاثي الأبعاد.",
    keyFeatures: "الميزات الرئيسية",
    dataSources: "مصادر البيانات",
    techStack: "المكدس التقني",
    openSource: "مفتوح المصدر",
    openSourceDesc: "Phoenix مفتوح المصدر بموجب ترخيص MIT. نرحب بالمساهمات!",
    viewOnGithub: "عرض على GitHub",
    footer: "تم بناؤه بعناية للاستجابة الإنسانية والتعافي من الكوارث.",
  },
  events: {
    title: "أحداث الكوارث",
    eventsFound: "أحداث تم العثور عليها",
    noEvents: "لم يتم العثور على أحداث",
    adjustFilters: "حاول ضبط الفلاتر",
    clearFilters: "مسح الفلاتر",
    affected: "متأثر",
    active: "نشط",
    location: "الموقع",
    severity: "الخطورة",
  },
  map: {
    globe3d: "الكرة الأرضية ثلاثية الأبعاد",
    view2d: "عرض ثنائي الأبعاد",
    satellite: "القمر الصناعي",
    dark: "داكن",
    activeEvents: "الأحداث النشطة",
    initializingGlobe: "جاري تهيئة الكرة الأرضية...",
  },
};

const ru: Translations = {
  common: {
    home: "Главная",
    events: "События",
    about: "О проекте",
    settings: "Настройки",
    search: "Поиск",
    searchPlaceholder: "Поиск событий, мест...",
    backToMap: "Назад к карте",
    loading: "Загрузка...",
    error: "Ошибка",
    retry: "Повторить",
    viewOnMap: "Посмотреть на карте",
  },
  settings: {
    title: "Настройки",
    subtitle: "Настройте Phoenix под себя",
    language: "Язык и регион",
    languageDesc: "Установите предпочитаемый язык интерфейса",
    displayLanguage: "Язык отображения",
    appearance: "Внешний вид",
    appearanceDesc: "Настройте визуальное оформление приложения",
    theme: "Тема",
    enableAnimations: "Включить анимации",
    animationsDesc: "Плавные переходы и визуальные эффекты",
    mapPreferences: "Настройки карты",
    mapPreferencesDesc: "Настройте параметры отображения карты по умолчанию",
    defaultBasemap: "Базовая карта по умолчанию",
    defaultView: "Вид по умолчанию",
    showClusterMarkers: "Показывать кластерные маркеры",
    clusterMarkersDesc: "Группировать близкие события в кластеры",
    dataSync: "Данные и синхронизация",
    dataSyncDesc: "Управление получением и обновлением данных",
    autoRefresh: "Автообновление",
    autoRefreshDesc: "Автоматически получать новые события",
    refreshInterval: "Интервал обновления",
    resetToDefaults: "Сбросить настройки",
    changesApplied: "Изменения применяются немедленно.",
    autoSaved: "Настройки автоматически сохраняются в браузере.",
  },
  about: {
    tagline: "Платформа цифрового двойника, где каждый может помочь исцелить раны Земли",
    description: "Phoenix — это глобальная открытая гуманитарная платформа, которая визуализирует катастрофы, войны и загрязнение окружающей среды в реальном времени через 3D цифровой двойник.",
    keyFeatures: "Ключевые функции",
    dataSources: "Источники данных",
    techStack: "Технологический стек",
    openSource: "Открытый исходный код",
    openSourceDesc: "Phoenix — проект с открытым исходным кодом под лицензией MIT. Мы рады вкладу!",
    viewOnGithub: "Смотреть на GitHub",
    footer: "Создано с заботой о гуманитарном реагировании и восстановлении после катастроф.",
  },
  events: {
    title: "События катастроф",
    eventsFound: "событий найдено",
    noEvents: "События не найдены",
    adjustFilters: "Попробуйте изменить фильтры",
    clearFilters: "Очистить фильтры",
    affected: "пострадавших",
    active: "Активно",
    location: "Местоположение",
    severity: "Серьезность",
  },
  map: {
    globe3d: "3D Глобус",
    view2d: "2D Вид",
    satellite: "Спутник",
    dark: "Темная",
    activeEvents: "Активные события",
    initializingGlobe: "Инициализация глобуса...",
  },
};

export const translations: Record<Language, Translations> = {
  en,
  ko,
  es,
  fr,
  zh,
  ar,
  ru,
};
