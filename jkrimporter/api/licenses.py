"""
Open Source Compliance / Third-Party Notices / SBOM

Kerää backendissä asennettujen Python-pakettien metatiedot ja lisenssit
Python-stdlib:n ``importlib.metadata``:n kautta. Tukee:

- JSON-listaus kaikista paketeista (SBOM-tyylinen)
- Yksittäisen paketin tarkemmat tiedot + lisenssitiedoston sisältö
- Tekstimuotoinen NOTICE-tiedosto (attribuutiovaatimus)
"""

from __future__ import annotations

import logging
import re
from importlib import metadata as importlib_metadata
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger("jkr-licenses")

# Tiedostonimet joita pidetään "lisenssitiedostoina" distin sisällä.
_LICENSE_FILE_PATTERNS = re.compile(
    r"(^|/)(LICEN[SC]E|COPYING|NOTICE|COPYRIGHT)(\.[A-Za-z0-9_-]+)?$",
    re.IGNORECASE,
)


def _clean(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if not value or value.upper() in {"UNKNOWN", "NONE"}:
        return None
    return value


def _license_from_classifiers(classifiers: Iterable[str]) -> List[str]:
    """Poimi OSI-hyväksytyt lisenssinimet Trove classifier -listasta."""
    out: List[str] = []
    for c in classifiers:
        if not c.startswith("License ::"):
            continue
        # "License :: OSI Approved :: MIT License" -> "MIT License"
        parts = [p.strip() for p in c.split("::")[1:] if p.strip()]
        if not parts:
            continue
        name = parts[-1]
        if name and name not in out:
            out.append(name)
    return out


def _summarize_license(meta: Any) -> Dict[str, Any]:
    """Poimi lisenssitiedot distin metadatasta.

    Core Metadata 2.4 tukee 'License-Expression' (SPDX) -kenttää; vanhempi
    'License' on vapaamuotoinen. Lisäksi Trove classifierit voivat kertoa
    lisenssin (esim. 'License :: OSI Approved :: MIT License').
    """
    license_expr = _clean(meta.get("License-Expression"))
    license_text = _clean(meta.get("License"))
    classifiers = meta.get_all("Classifier") or []
    license_classifiers = _license_from_classifiers(classifiers)

    # Näytettävä pääarvo: SPDX-expression > classifier > freeform license
    if license_expr:
        display = license_expr
    elif license_classifiers:
        display = ", ".join(license_classifiers)
    elif license_text and len(license_text) <= 200:
        display = license_text
    else:
        display = None

    return {
        "license": display,
        "license_expression": license_expr,
        "license_classifiers": license_classifiers,
        # Vapaamuotoinen License-kenttä voi olla kokonaisia rivejä lisenssitekstiä –
        # palautetaan se mahdolliseen tarkempaan tarkasteluun, mutta ei listassa.
        "license_raw": license_text,
    }


def _extract_url(meta: Any, label: str) -> Optional[str]:
    """Hae Project-URL-kentästä tietty rooli (esim. 'Homepage', 'Source')."""
    urls = meta.get_all("Project-URL") or []
    target = label.lower()
    for entry in urls:
        if "," not in entry:
            continue
        role, url = entry.split(",", 1)
        if role.strip().lower() == target:
            return url.strip()
    return None


def list_distributions() -> List[Dict[str, Any]]:
    """Palauta lista asennetuista Python-distribuutioista metatietoineen."""
    results: List[Dict[str, Any]] = []
    seen = set()
    for dist in importlib_metadata.distributions():
        meta = dist.metadata
        if meta is None:
            continue
        name = _clean(meta.get("Name")) or _clean(getattr(dist, "name", None))
        if not name:
            continue
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)

        lic = _summarize_license(meta)
        homepage = _clean(meta.get("Home-page")) or _extract_url(meta, "Homepage")
        results.append({
            "name": name,
            "version": _clean(meta.get("Version")),
            "summary": _clean(meta.get("Summary")),
            "license": lic["license"],
            "license_expression": lic["license_expression"],
            "license_classifiers": lic["license_classifiers"],
            "author": _clean(meta.get("Author")),
            "author_email": _clean(meta.get("Author-email")),
            "homepage": homepage,
            "source": _extract_url(meta, "Source") or _extract_url(meta, "Repository"),
        })
    results.sort(key=lambda r: (r.get("name") or "").lower())
    return results


def get_distribution(name: str) -> Dict[str, Any]:
    """Palauta yksittäisen distin täydet tiedot + löydetyt lisenssitiedostot."""
    try:
        dist = importlib_metadata.distribution(name)
    except importlib_metadata.PackageNotFoundError:
        raise LookupError(name)

    meta = dist.metadata
    lic = _summarize_license(meta)

    license_files: List[Dict[str, Any]] = []
    for f in (dist.files or []):
        path_str = str(f)
        if _LICENSE_FILE_PATTERNS.search(path_str):
            try:
                content = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    content = f.read_text(encoding="latin-1")
                except Exception:
                    content = None
            except Exception:
                content = None
            license_files.append({
                "path": path_str,
                "content": content,
            })

    homepage = _clean(meta.get("Home-page")) or _extract_url(meta, "Homepage")
    return {
        "name": _clean(meta.get("Name")) or name,
        "version": _clean(meta.get("Version")),
        "summary": _clean(meta.get("Summary")),
        "description": _clean(meta.get("Description")),
        "license": lic["license"],
        "license_expression": lic["license_expression"],
        "license_classifiers": lic["license_classifiers"],
        "license_raw": lic["license_raw"],
        "license_files": license_files,
        "author": _clean(meta.get("Author")),
        "author_email": _clean(meta.get("Author-email")),
        "homepage": homepage,
        "source": _extract_url(meta, "Source") or _extract_url(meta, "Repository"),
        "requires": list(meta.get_all("Requires-Dist") or []),
        "requires_python": _clean(meta.get("Requires-Python")),
    }


def render_notices_text(distributions: List[Dict[str, Any]]) -> str:
    """Muodosta tekstimuotoinen THIRD-PARTY-NOTICES."""
    lines: List[str] = []
    lines.append("THIRD-PARTY NOTICES")
    lines.append("=" * 70)
    lines.append("")
    lines.append(
        "Tämä sovellus käyttää seuraavia kolmannen osapuolen avoimen lähdekoodin "
        "kirjastoja. Alla on listattu kunkin paketin nimi, versio, lisenssi ja "
        "kotisivu attribuutiovaatimuksen täyttämiseksi."
    )
    lines.append("")
    for d in distributions:
        lines.append(f"- {d.get('name')} {d.get('version') or ''}".rstrip())
        if d.get("license"):
            lines.append(f"  Lisenssi: {d['license']}")
        if d.get("homepage"):
            lines.append(f"  Kotisivu: {d['homepage']}")
        if d.get("author"):
            lines.append(f"  Tekijä: {d['author']}")
        if d.get("summary"):
            lines.append(f"  Kuvaus: {d['summary']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
