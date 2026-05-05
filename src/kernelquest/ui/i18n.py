"""Phase 11 — minimal translation layer.

Two locales today: English (``en``, default) and Turkish (``tr``).  Strings are
addressed by short stable keys.  Missing keys fall back to the English copy or,
as a last resort, the key itself — never a crash, never a blank UI.
"""

from __future__ import annotations

from typing import Final

# Active language code. ``set_language()`` mutates this; renderers read it via
# ``t()`` on every frame so the toggle is immediate.
_current: str = "en"

SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = ("en", "tr")


_EN: Final[dict[str, str]] = {
    # Menu options + meta.
    "menu.new_run": "New Run",
    "menu.daily_run": "Daily Run",
    "menu.training": "Training",
    "menu.howtoplay": "How to Play",
    "menu.codex": "Codex",
    "menu.high_scores": "High Scores",
    "menu.daily_board": "Daily Board",
    "menu.stats": "Stats",
    "menu.shop": "Shop",
    "menu.settings": "Settings",
    "menu.quit": "Quit",
    "menu.hint": "[↑/↓] navigate   [ENTER] select   [ESC] quit",
    # Settings labels.
    "settings.title": "SETTINGS",
    "settings.music_vol": "Music Vol",
    "settings.sfx_vol": "SFX Vol",
    "settings.mute": "Mute",
    "settings.difficulty": "Difficulty",
    "settings.theme": "Theme",
    "settings.fullscreen": "Fullscreen",
    "settings.ui_scale": "UI Scale",
    "settings.reduce_motion": "Reduce Motion",
    "settings.crt": "CRT Effect",
    "settings.large_text": "Large Text",
    "settings.palette": "Player Palette",
    "settings.auto_skip_intro": "Auto-skip Intro",
    "settings.language": "Language",
    "settings.on": "ON",
    "settings.off": "OFF",
    # Distro select.
    "distro.title": "SELECT DISTRO",
    "distro.title_daily": "SELECT DISTRO — DAILY",
    "distro.locked": "??? (locked)",
    "distro.confirm": "[ENTER] boot   [ESC] back",
    "distro.hint": "[UP/DN] select   [ENTER] boot   [ESC] back",
    "distro.unlock_hint": "Unlock: clear a run with the previous distro.",
    "distro.signature": "signature",
    "distro.start_kit": "starting kit",
    # Per-distro copy.
    "distro.vanilla.name": "Vanilla",
    "distro.vanilla.desc": "Baseline starting kit. No bonuses, no penalties.",
    "distro.vanilla.signature": "No twist — the reference build.",
    "distro.vanilla.unlock": "Always available.",
    "distro.minimal.name": "Minimal",
    "distro.minimal.desc": "Fewer cycles, but +50% bits from kills.",
    "distro.minimal.signature": "Lean ops: every kill banks more bits.",
    "distro.minimal.unlock": "Clear a run on Vanilla.",
    "distro.hardened.name": "Hardened",
    "distro.hardened.desc": "+20 starting RAM, programs cost +1 cycle.",
    "distro.hardened.signature": "Defensive build: tankier but slower programs.",
    "distro.hardened.unlock": "Clear a run on Minimal.",
    "distro.realtime.name": "Realtime",
    "distro.realtime.desc": "Enemies act first, but +1 free move every 5 turns.",
    "distro.realtime.signature": "Reactive ops with periodic free turns.",
    "distro.realtime.unlock": "Clear a run on Hardened.",
    "distro.bleeding_edge.name": "Bleeding-Edge",
    "distro.bleeding_edge.desc": "Start with 2 random Daemons; RAM regen disabled.",
    "distro.bleeding_edge.signature": "Two random daemons online from t=0.",
    "distro.bleeding_edge.unlock": "Clear a run on Realtime.",
    "distro.recovery.name": "Recovery",
    "distro.recovery.desc": "Built around init(0). Starts with cron + restore --from-snapshot.",
    "distro.recovery.signature": "Snapshot-based comeback toolkit.",
    "distro.recovery.unlock": "Clear a run on Bleeding-Edge.",
    # Run / Release ladder.
    "ladder.title": "RELEASE LADDER",
    "ladder.release": "Release",
    "ladder.target": "Target",
    "ladder.score": "Score",
    "ladder.skipped": "SKIPPED",
    "ladder.cleared": "CLEAR",
    "ladder.boss": "BOSS",
    # Milestone result.
    "milestone.title": "MILESTONE RESULT",
    "milestone.score_label": "Score",
    "milestone.target_label": "Target",
    "milestone.bits_earned": "Bits earned",
    "milestone.continue": "[ENTER] continue   [V] vendor   [S] skip (non-boss only)",
    "milestone.failed": "TARGET MISSED — run terminated.",
    "milestone.cleared": "CLEARED",
    "milestone.target_hit": "TARGET HIT — bonus bits!",
    "milestone.target_missed": "target missed — milestone still cleared",
    "milestone.release": "Release",
    "milestone.milestone": "Milestone",
    "milestone.score": "Score",
    "milestone.target": "Target",
    "milestone.bits": "Bits",
    "milestone.hint": "[ENTER] continue   [S] skip   [V] vendor",
    "milestone.hint_boss": "[ENTER] continue",
    "milestone.skip_tag_awarded": "Skip tag granted: {tag}",
    # Vendor (in-run shop).
    "vendor.title": "VENDOR",
    "vendor.bits": "Bits: {bits}",
    "vendor.reroll": "Reroll (3 bits)",
    "vendor.leave": "Leave",
    "vendor.bought": "purchased",
    "vendor.too_poor": "not enough bits",
    "vendor.empty": "(stock empty)",
    "vendor.free": "FREE VENDOR",
    "vendor.free_cost": "FREE",
    "vendor.hint": "[UP/DN] select   [ENTER] buy   [ESC] leave",
    # Run summary.
    "summary.title": "RUN SUMMARY",
    "summary.title_success": "RUN SUCCESSFUL",
    "summary.title_failed": "RUN FAILED",
    "summary.success": "RUN SUCCESSFUL",
    "summary.failed": "RUN FAILED",
    "summary.releases_cleared": "Releases cleared",
    "summary.bits_to_meta": "Bits banked",
    "summary.next_distro": "New distro unlocked",
    "summary.unlocked": "Unlocked",
    "summary.distro": "Distro",
    "summary.score": "Score",
    "summary.hint": "[ENTER] return to menu",
    "summary.return": "[ENTER] return to menu",
    # HUD.
    "hud.sector": "Sector",
    "hud.process": "Process",
    "hud.ram": "RAM",
    "hud.cycles": "CYCLES",
    "hud.score": "SCORE",
    "hud.cache": "CACHE",
    "hud.programs": "PROGRAMS",
    "hud.daemons": "DAEMONS",
    "hud.patches": "PATCHES",
    "hud.distro": "Distro",
    # Console / events.
    "console.boss_loaded": "BOSS PROCESS LOADED",
    "console.exit_locked": "EXIT LOCKED — terminate {boss} first.",
    "console.exit_unlocked": "BOSS terminated. EXIT unlocked.",
    "console.run_success": "[init] uptime certified — kernel stable.",
    # Generic.
    "generic.back": "[ESC] back",
    "generic.unknown": "?",
    "generic.yes": "yes",
    "generic.no": "no",
}


_TR: Final[dict[str, str]] = {
    # Menu.
    "menu.new_run": "Yeni Çalıştırma",
    "menu.daily_run": "Günlük Çalıştırma",
    "menu.training": "Eğitim",
    "menu.howtoplay": "Nasıl Oynanır",
    "menu.codex": "Kodeks",
    "menu.high_scores": "Yüksek Skorlar",
    "menu.daily_board": "Günlük Tablo",
    "menu.stats": "İstatistik",
    "menu.shop": "Mağaza",
    "menu.settings": "Ayarlar",
    "menu.quit": "Çıkış",
    "menu.hint": "[↑/↓] gez   [ENTER] seç   [ESC] çık",
    # Settings.
    "settings.title": "AYARLAR",
    "settings.music_vol": "Müzik Sesi",
    "settings.sfx_vol": "Efekt Sesi",
    "settings.mute": "Sessiz",
    "settings.difficulty": "Zorluk",
    "settings.theme": "Tema",
    "settings.fullscreen": "Tam Ekran",
    "settings.ui_scale": "Arayüz Ölçeği",
    "settings.reduce_motion": "Hareketi Azalt",
    "settings.crt": "CRT Efekti",
    "settings.large_text": "Büyük Yazı",
    "settings.palette": "Oyuncu Paleti",
    "settings.auto_skip_intro": "Girişi Otomatik Atla",
    "settings.language": "Dil",
    "settings.on": "AÇIK",
    "settings.off": "KAPALI",
    # Distro.
    "distro.title": "DAĞITIM SEÇ",
    "distro.title_daily": "DAĞITIM SEÇ — GÜNLÜK",
    "distro.locked": "??? (kilitli)",
    "distro.confirm": "[ENTER] başlat   [ESC] geri",
    "distro.hint": "[YUKARI/AŞAĞI] seç   [ENTER] başlat   [ESC] geri",
    "distro.unlock_hint": "Açmak için: önceki dağıtımla bir koşuyu tamamla.",
    "distro.signature": "imza yetenek",
    "distro.start_kit": "başlangıç kiti",
    # Dağıtım bilgileri.
    "distro.vanilla.name": "Vanilya",
    "distro.vanilla.desc": "Standart başlangıç kiti. Bonus yok, ceza yok.",
    "distro.vanilla.signature": "Sürprizsiz — referans yapılandırma.",
    "distro.vanilla.unlock": "Her zaman açık.",
    "distro.minimal.name": "Minimal",
    "distro.minimal.desc": "Daha az döngü, ama öldürmelerden +%50 bit.",
    "distro.minimal.signature": "Yalın operasyon: her öldürme daha fazla bit.",
    "distro.minimal.unlock": "Vanilya ile bir koşuyu tamamla.",
    "distro.hardened.name": "Sertleştirilmiş",
    "distro.hardened.desc": "+20 başlangıç RAM’ı; programlar +1 döngü daha pahalı.",
    "distro.hardened.signature": "Savunma odaklı: daha tank, daha yavaş programlar.",
    "distro.hardened.unlock": "Minimal ile bir koşuyu tamamla.",
    "distro.realtime.name": "Gerçek-zamanlı",
    "distro.realtime.desc": "Düşmanlar önce hareket eder, ama her 5 turda 1 bedava hamle.",
    "distro.realtime.signature": "Reaktif oyun, periyodik bedava turlar.",
    "distro.realtime.unlock": "Sertleştirilmiş ile bir koşuyu tamamla.",
    "distro.bleeding_edge.name": "Sınır-Teknoloji",
    "distro.bleeding_edge.desc": "2 rastgele Daemon ile başlarsan; RAM yenilenmesi kapalı.",
    "distro.bleeding_edge.signature": "Başlangıçtan iki rastgele daemon aktif.",
    "distro.bleeding_edge.unlock": "Gerçek-zamanlı ile bir koşuyu tamamla.",
    "distro.recovery.name": "Kurtarma",
    "distro.recovery.desc": "init(0) üzerine kurulu. cron + restore --from-snapshot ile başlar.",
    "distro.recovery.signature": "Anlık-görüntü tabanlı geri dönüş kiti.",
    "distro.recovery.unlock": "Sınır-Teknoloji ile bir koşuyu tamamla.",
    # Ladder.
    "ladder.title": "SÜRÜM MERDİVENİ",
    "ladder.release": "Sürüm",
    "ladder.target": "Hedef",
    "ladder.score": "Skor",
    "ladder.skipped": "ATLANDI",
    "ladder.cleared": "TAMAM",
    "ladder.boss": "BOSS",
    # Milestone result.
    "milestone.title": "KİLOMETRE TAŞI SONUCU",
    "milestone.score_label": "Skor",
    "milestone.target_label": "Hedef",
    "milestone.bits_earned": "Kazanılan bit",
    "milestone.continue": "[ENTER] devam   [V] satıcı   [S] atla (bossta yok)",
    "milestone.failed": "HEDEF TUTTURULAMADI — koşu bitti.",
    "milestone.cleared": "GEÇİLDİ",
    "milestone.target_hit": "HEDEF TUTTU — bonus bit!",
    "milestone.target_missed": "hedef tutmadı — yine de geçildi",
    "milestone.release": "Sürüm",
    "milestone.milestone": "Kilometre taşı",
    "milestone.score": "Skor",
    "milestone.target": "Hedef",
    "milestone.bits": "Bit",
    "milestone.hint": "[ENTER] devam   [S] atla   [V] satıcı",
    "milestone.hint_boss": "[ENTER] devam",
    "milestone.skip_tag_awarded": "Atlama etiketi: {tag}",
    # Vendor.
    "vendor.title": "SATICI",
    "vendor.bits": "Bit: {bits}",
    "vendor.reroll": "Yenile (3 bit)",
    "vendor.leave": "Ayrıl",
    "vendor.bought": "satın alındı",
    "vendor.too_poor": "yetersiz bit",
    "vendor.empty": "(stok boş)",
    "vendor.free": "BEDAVA SATICI",
    "vendor.free_cost": "BEDAVA",
    "vendor.hint": "[YUKARI/AŞAĞI] seç   [ENTER] al   [ESC] ayrıl",
    # Summary.
    "summary.title": "KOŞU ÖZETİ",
    "summary.title_success": "KOŞU BAŞARILI",
    "summary.title_failed": "KOŞU BAŞARISIZ",
    "summary.success": "KOŞU BAŞARILI",
    "summary.failed": "KOŞU BAŞARISIZ",
    "summary.releases_cleared": "Tamamlanan sürüm",
    "summary.bits_to_meta": "Bankaya yazılan bit",
    "summary.next_distro": "Yeni dağıtım açıldı",
    "summary.unlocked": "Açıldı",
    "summary.distro": "Dağıtım",
    "summary.score": "Skor",
    "summary.hint": "[ENTER] menüye dön",
    "summary.return": "[ENTER] menüye dön",
    # HUD.
    "hud.sector": "Sektör",
    "hud.process": "Süreç",
    "hud.ram": "RAM",
    "hud.cycles": "DÖNGÜ",
    "hud.score": "SKOR",
    "hud.cache": "ÖNBELLEK",
    "hud.programs": "PROGRAMLAR",
    "hud.daemons": "DAEMONLAR",
    "hud.patches": "YAMALAR",
    "hud.distro": "Dağıtım",
    # Console.
    "console.boss_loaded": "BOSS SÜRECİ YÜKLENDİ",
    "console.exit_locked": "ÇIKIŞ KİLİTLİ — önce {boss} sonlandır.",
    "console.exit_unlocked": "BOSS sonlandırıldı. ÇIKIŞ açıldı.",
    "console.run_success": "[init] uptime onaylandı — çekirdek stabil.",
    # Generic.
    "generic.back": "[ESC] geri",
    "generic.unknown": "?",
    "generic.yes": "evet",
    "generic.no": "hayır",
}


_TABLES: Final[dict[str, dict[str, str]]] = {"en": _EN, "tr": _TR}


def set_language(code: str) -> None:
    """Switch the active locale. Unknown codes silently fall back to English."""
    global _current
    _current = code if code in _TABLES else "en"


def get_language() -> str:
    return _current


def t(key: str, **kwargs: object) -> str:
    """Translate ``key`` for the active language with optional ``str.format`` args."""
    table = _TABLES.get(_current, _EN)
    template = table.get(key) or _EN.get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def cycle_language(direction: int = 1) -> str:
    """Advance through ``SUPPORTED_LANGUAGES`` and return the new code."""
    idx = SUPPORTED_LANGUAGES.index(_current) if _current in SUPPORTED_LANGUAGES else 0
    idx = (idx + direction) % len(SUPPORTED_LANGUAGES)
    set_language(SUPPORTED_LANGUAGES[idx])
    return _current
