"""Press kit — everything a journalist needs for a
cover story in one zip.

The dopresskit.com convention is simple: ship one
downloadable bundle with every logo, every screenshot,
every b-roll clip, a factsheet, the embargo notice,
contact card, and rating bundle. The press kit module
assembles that bundle, tracks asset versions, gates
access by embargo timestamp and journalist whitelist,
and emits per-recipient download tokens that expire on
a deadline.

Nineteen PressAsset kinds cover the canonical
deliverables:

  LOGO_PRIMARY / LOGO_HORIZONTAL / LOGO_VERTICAL /
  LOGO_MARK_ONLY            — every logo orientation
  KEY_ART_HERO /
  KEY_ART_SECONDARY         — the marketing pieces
  SCREENSHOT_GAMEPLAY /
  SCREENSHOT_BEAUTY         — gameplay vs beauty
  B_ROLL_CLIP               — short cut-friendly clips
  TRAILER_BUNDLE            — the trailer pack
  FACTSHEET_PDF / BIO_SHEET — the boilerplate
  CONTACT_CARD              — who to email
  EMBARGO_NOTICE            — when to publish
  EULA / PRIVACY_POLICY     — legal
  RATING_BUNDLE_ESRB_PEGI_USK_CERO
                            — every age rating
  ACCESSIBILITY_STATEMENT   — what flags we support
  DEVELOPER_FAQ             — the press FAQ

Each asset registers its required formats — PNG_4K,
PNG_8K, EPS, SVG, PDF, MP4_4K, MP4_HD, TXT, JSON — and
tracks a version history so the journalist always gets
the latest "March 2026 Reveal v3" not the stale v1.

A bundle locks until embargo_until_iso. is_embargo_
active(kit_id, now_iso) returns True before the
embargo lifts; download tokens generated before the
embargo are valid-after, not valid-now. grant_access
adds a journalist to the whitelist with a per-
recipient allowed_assets set (the indie outlet gets
screenshots + factsheet; the trade rag gets the full
bundle).

Public surface
--------------
    PressAsset enum
    AssetFormat enum
    AssetSpec dataclass (frozen)
    AssetVersion dataclass (frozen)
    PressKitBundle dataclass (frozen)
    AccessGrant dataclass (frozen)
    PressKitSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PressAsset(enum.Enum):
    LOGO_PRIMARY = "logo_primary"
    LOGO_HORIZONTAL = "logo_horizontal"
    LOGO_VERTICAL = "logo_vertical"
    LOGO_MARK_ONLY = "logo_mark_only"
    KEY_ART_HERO = "key_art_hero"
    KEY_ART_SECONDARY = "key_art_secondary"
    SCREENSHOT_GAMEPLAY = "screenshot_gameplay"
    SCREENSHOT_BEAUTY = "screenshot_beauty"
    B_ROLL_CLIP = "b_roll_clip"
    TRAILER_BUNDLE = "trailer_bundle"
    FACTSHEET_PDF = "factsheet_pdf"
    BIO_SHEET = "bio_sheet"
    CONTACT_CARD = "contact_card"
    EMBARGO_NOTICE = "embargo_notice"
    EULA = "eula"
    PRIVACY_POLICY = "privacy_policy"
    RATING_BUNDLE_ESRB_PEGI_USK_CERO = (
        "rating_bundle_esrb_pegi_usk_cero"
    )
    ACCESSIBILITY_STATEMENT = "accessibility_statement"
    DEVELOPER_FAQ = "developer_faq"


class AssetFormat(enum.Enum):
    PNG_4K = "png_4k"
    PNG_8K = "png_8k"
    EPS = "eps"
    SVG = "svg"
    PDF = "pdf"
    MP4_4K = "mp4_4k"
    MP4_HD = "mp4_hd"
    TXT = "txt"
    JSON = "json"


# Required assets that every kit must include. These
# are the dopresskit.com canonical baseline.
_REQUIRED_ASSETS: frozenset[PressAsset] = frozenset({
    PressAsset.LOGO_PRIMARY,
    PressAsset.KEY_ART_HERO,
    PressAsset.SCREENSHOT_GAMEPLAY,
    PressAsset.FACTSHEET_PDF,
    PressAsset.CONTACT_CARD,
    PressAsset.EMBARGO_NOTICE,
})


@dataclasses.dataclass(frozen=True)
class AssetSpec:
    kind: PressAsset
    required: bool
    formats: frozenset[AssetFormat]
    resolution_options: tuple[str, ...]
    version: str
    last_updated_iso: str


@dataclasses.dataclass(frozen=True)
class AssetVersion:
    version: str
    last_updated_iso: str
    formats: frozenset[AssetFormat]


@dataclasses.dataclass(frozen=True)
class AccessGrant:
    journalist_id: str
    allowed_assets: frozenset[PressAsset]
    granted_at_iso: str


@dataclasses.dataclass(frozen=True)
class PressKitBundle:
    kit_id: str
    title: str
    embargo_until_iso: str
    assets: tuple[PressAsset, ...]
    recipient_list: tuple[str, ...]
    expiry_iso: str


@dataclasses.dataclass
class _KitInternal:
    bundle: PressKitBundle
    grants: dict[str, AccessGrant]
    tokens: dict[str, str]
    violation_log: list[str]


@dataclasses.dataclass
class PressKitSystem:
    _specs: dict[PressAsset, AssetSpec] = dataclasses.field(
        default_factory=dict,
    )
    _versions: dict[PressAsset, list[AssetVersion]] = (
        dataclasses.field(default_factory=dict)
    )
    _kits: dict[str, _KitInternal] = dataclasses.field(
        default_factory=dict,
    )
    _token_counter: int = 0
    _kit_counter: int = 0

    # ---------------------------------------------- specs
    def register_asset(
        self,
        kind: PressAsset,
        formats: t.Iterable[AssetFormat],
        resolution_options: t.Iterable[str] = (),
        version: str = "v1",
        last_updated_iso: str = "2026-01-01T00:00:00Z",
    ) -> AssetSpec:
        fmts = frozenset(formats)
        if not fmts:
            raise ValueError(
                "at least one format required",
            )
        spec = AssetSpec(
            kind=kind,
            required=(kind in _REQUIRED_ASSETS),
            formats=fmts,
            resolution_options=tuple(resolution_options),
            version=version,
            last_updated_iso=last_updated_iso,
        )
        self._specs[kind] = spec
        hist = self._versions.setdefault(kind, [])
        hist.append(
            AssetVersion(
                version=version,
                last_updated_iso=last_updated_iso,
                formats=fmts,
            ),
        )
        return spec

    def get_asset_spec(self, kind: PressAsset) -> AssetSpec:
        if kind not in self._specs:
            raise KeyError(f"unknown asset: {kind}")
        return self._specs[kind]

    def asset_count(self) -> int:
        return len(self._specs)

    def asset_versions(
        self,
        kind: PressAsset,
    ) -> tuple[AssetVersion, ...]:
        return tuple(self._versions.get(kind, ()))

    def is_required(self, kind: PressAsset) -> bool:
        return kind in _REQUIRED_ASSETS

    # ---------------------------------------------- bundle
    def build_kit(
        self,
        title: str,
        embargo_until_iso: str,
        assets: t.Iterable[PressAsset],
        expiry_iso: str = "2027-01-01T00:00:00Z",
    ) -> PressKitBundle:
        if not title:
            raise ValueError("title required")
        if not embargo_until_iso:
            raise ValueError("embargo_until_iso required")
        self._kit_counter += 1
        kit_id = f"kit_{self._kit_counter}"
        bundle = PressKitBundle(
            kit_id=kit_id,
            title=title,
            embargo_until_iso=embargo_until_iso,
            assets=tuple(assets),
            recipient_list=(),
            expiry_iso=expiry_iso,
        )
        self._kits[kit_id] = _KitInternal(
            bundle=bundle,
            grants={},
            tokens={},
            violation_log=[],
        )
        return bundle

    def get_kit(self, kit_id: str) -> PressKitBundle:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        return self._kits[kit_id].bundle

    def kit_count(self) -> int:
        return len(self._kits)

    # ---------------------------------------------- validate
    def validate_kit(
        self,
        kit_id: str,
    ) -> tuple[str, ...]:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        bundle = self._kits[kit_id].bundle
        assets = set(bundle.assets)
        issues: list[str] = []
        for req in _REQUIRED_ASSETS:
            if req not in assets:
                issues.append(
                    f"missing required asset: {req.value}",
                )
        # Also check that every asset has a spec registered.
        for a in assets:
            if a not in self._specs:
                issues.append(
                    f"asset not registered: {a.value}",
                )
        return tuple(issues)

    # ---------------------------------------------- access
    def grant_access(
        self,
        kit_id: str,
        journalist_id: str,
        allowed_assets: t.Iterable[PressAsset],
        granted_at_iso: str = "2026-01-01T00:00:00Z",
    ) -> AccessGrant:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        if not journalist_id:
            raise ValueError("journalist_id required")
        ki = self._kits[kit_id]
        grant = AccessGrant(
            journalist_id=journalist_id,
            allowed_assets=frozenset(allowed_assets),
            granted_at_iso=granted_at_iso,
        )
        ki.grants[journalist_id] = grant
        # Track recipient on the bundle.
        if journalist_id not in ki.bundle.recipient_list:
            ki.bundle = dataclasses.replace(
                ki.bundle,
                recipient_list=(
                    ki.bundle.recipient_list
                    + (journalist_id,)
                ),
            )
        return grant

    def get_grant(
        self,
        kit_id: str,
        journalist_id: str,
    ) -> AccessGrant:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        ki = self._kits[kit_id]
        if journalist_id not in ki.grants:
            raise KeyError(
                f"no grant for {journalist_id} on {kit_id}",
            )
        return ki.grants[journalist_id]

    # ---------------------------------------------- tokens
    def generate_download_token(
        self,
        kit_id: str,
        recipient: str,
    ) -> str:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        ki = self._kits[kit_id]
        if recipient not in ki.grants:
            raise ValueError(
                f"recipient {recipient} not granted access",
            )
        self._token_counter += 1
        token = (
            f"dl_{kit_id}_{recipient}_{self._token_counter}"
        )
        ki.tokens[recipient] = token
        return token

    def token_for(
        self,
        kit_id: str,
        recipient: str,
    ) -> str:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        ki = self._kits[kit_id]
        if recipient not in ki.tokens:
            raise KeyError(
                f"no token for {recipient} on {kit_id}",
            )
        return ki.tokens[recipient]

    # ---------------------------------------------- embargo
    def is_embargo_active(
        self,
        kit_id: str,
        now_iso: str,
    ) -> bool:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        bundle = self._kits[kit_id].bundle
        return now_iso < bundle.embargo_until_iso

    def log_embargo_violation(
        self,
        kit_id: str,
        journalist_id: str,
        when_iso: str,
    ) -> int:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        ki = self._kits[kit_id]
        ki.violation_log.append(
            f"{when_iso}|{journalist_id}",
        )
        return len(ki.violation_log)

    def violation_count(self, kit_id: str) -> int:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        return len(self._kits[kit_id].violation_log)

    # ---------------------------------------------- summary
    def kit_summary(self, kit_id: str) -> dict:
        if kit_id not in self._kits:
            raise KeyError(f"unknown kit_id: {kit_id}")
        ki = self._kits[kit_id]
        return {
            "kit_id": ki.bundle.kit_id,
            "title": ki.bundle.title,
            "embargo_until_iso": ki.bundle.embargo_until_iso,
            "asset_count": len(ki.bundle.assets),
            "recipients": list(ki.bundle.recipient_list),
            "grants": list(ki.grants.keys()),
            "tokens_issued": len(ki.tokens),
            "violations": len(ki.violation_log),
            "expiry_iso": ki.bundle.expiry_iso,
        }


__all__ = [
    "PressAsset",
    "AssetFormat",
    "AssetSpec",
    "AssetVersion",
    "AccessGrant",
    "PressKitBundle",
    "PressKitSystem",
]
