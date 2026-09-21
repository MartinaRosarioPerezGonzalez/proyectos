import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple
import requests

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

PRODUCT_ASSETS_BASE_URL = os.getenv(
    "PRODUCT_ASSETS_BASE_URL",
    "https://product-assets-api.2bgiw781jy8e.us-south.codeengine.appdomain.cloud"
).rstrip("/")


def _load_catalog() -> List[Dict[str, Any]]:
    """
    Loads the product catalog from the Code Engine API.
    Falls back to a minimal error response if the request fails.
    """
    try:
        catalog_url = f"{PRODUCT_ASSETS_BASE_URL}/catalog"
        response = requests.get(catalog_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # Log the error and return empty catalog
        print(f"Error loading catalog from {PRODUCT_ASSETS_BASE_URL}/catalog: {e}")
        return []


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def _as_set(values: List[str]) -> Set[str]:
    return {_normalize(v) for v in values}


def _score_product(criteria: Dict[str, Any], candidate: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    Score a product based on how well it matches the search criteria.
    Returns a tuple of (score, reasons).
    """
    score = 0
    reasons: List[str] = []

    # Match brand (Rosamonte, Amanda)
    if criteria.get("brand") and candidate["brand"].lower() == criteria["brand"].lower():
        score += 30
        reasons.append(f"marca {candidate['brand']}")

    # Match intensity (Suave, Media, Intensa)
    if criteria.get("intensity") and candidate["intensity"].lower() == criteria["intensity"].lower():
        score += 25
        reasons.append(f"intensidad {candidate['intensity'].lower()}")

    # Match grind type (Fina, Media, Gruesa)
    if criteria.get("grind") and candidate["grind"].lower() == criteria["grind"].lower():
        score += 20
        reasons.append(f"molienda {candidate['grind'].lower()}")

    # Match with/without stem
    if criteria.get("with_stem") is not None and candidate["with_stem"] == criteria["with_stem"]:
        score += 20
        stem_text = "con palo" if candidate["with_stem"] else "sin palo"
        reasons.append(stem_text)

    # Match recommended for (principiantes, consumidores habituales, etc.)
    if criteria.get("recommended_for"):
        candidate_rec = _as_set(candidate.get("recommended_for", []))
        criteria_rec = _as_set([criteria["recommended_for"]])
        if candidate_rec & criteria_rec:
            score += 25
            reasons.append(f"recomendado para {criteria['recommended_for']}")

    # Match consumption occasion
    if criteria.get("occasion"):
        candidate_occasions = _as_set(candidate.get("consumption_occasions", []))
        if _normalize(criteria["occasion"]) in candidate_occasions:
            score += 15
            reasons.append(f"ideal para {criteria['occasion']}")

    # Match flavor profile keywords
    if criteria.get("flavor_keywords"):
        candidate_flavor = _normalize(candidate.get("flavor_profile", ""))
        criteria_keywords = _as_set(criteria["flavor_keywords"])
        matches = [kw for kw in criteria_keywords if kw in candidate_flavor]
        if matches:
            score += min(15, 5 * len(matches))
            reasons.append(f"perfil de sabor: {', '.join(matches)}")

    return score, reasons


def _format_attributes(product: Dict[str, Any]) -> str:
    """Format product attributes for display."""
    stem_text = "Con palo" if product["with_stem"] else "Sin palo"
    return (
        f"- Marca: {product['brand']}\n"
        f"- Tipo: {product['type']}\n"
        f"- Intensidad: {product['intensity']}\n"
        f"- Molienda: {product['grind']}\n"
        f"- {stem_text}\n"
        f"- Formato: {product['format']}\n"
        f"- Tamaño: {product['size']}\n"
        f"- Perfil de sabor: {product['flavor_profile']}\n"
        f"- Recomendado para: {', '.join(product['recommended_for'])}"
    )


@tool(permission=ToolPermission.READ_ONLY)
def recommend_visual_products(
    intensity: Optional[str] = None,
    with_stem: Optional[bool] = None,
    brand: Optional[str] = None,
    recommended_for: Optional[str] = None,
    occasion: Optional[str] = None,
    grind: Optional[str] = None,
    flavor_keywords: Optional[List[str]] = None,
    max_results: int = 2
) -> str:
    """
    Recomienda productos de yerba mate Las Marías desde el catálogo visual estructurado
    y devuelve Markdown con imágenes inline de cada producto.

    Args:
        intensity: Intensidad deseada (Suave, Media, Intensa). Opcional.
        with_stem: True para yerba con palo, False para sin palo (despalada). Opcional.
        brand: Marca deseada (Rosamonte, Amanda). Opcional.
        recommended_for: Perfil del consumidor (principiantes, consumidores habituales, paladares exigentes). Opcional.
        occasion: Ocasión de consumo (oficina, hogar, viaje, etc.). Opcional.
        grind: Tipo de molienda (Fina, Media, Gruesa). Opcional.
        flavor_keywords: Palabras clave del perfil de sabor (suave, intenso, equilibrado, etc.). Opcional.
        max_results: Número máximo de productos a recomendar. Por defecto 2.

    Returns:
        Markdown con recomendaciones de productos, explicaciones e imágenes inline.
    """
    catalog = _load_catalog()

    if not catalog:
        return (
            "No se pudo cargar el catálogo de productos. "
            "Por favor, intentá nuevamente más tarde."
        )

    # Build search criteria from provided parameters
    criteria = {}
    if intensity:
        criteria["intensity"] = intensity
    if with_stem is not None:
        criteria["with_stem"] = with_stem
    if brand:
        criteria["brand"] = brand
    if recommended_for:
        criteria["recommended_for"] = recommended_for
    if occasion:
        criteria["occasion"] = occasion
    if grind:
        criteria["grind"] = grind
    if flavor_keywords:
        criteria["flavor_keywords"] = flavor_keywords

    # If no criteria provided, return all products
    if not criteria:
        response_parts = ["**Productos disponibles en el catálogo Las Marías:**", ""]
        for product in catalog[:max_results]:
            image_url = f"{PRODUCT_ASSETS_BASE_URL}/images/{product['image_file']}"
            response_parts.extend([
                f"**{product['product']}** (SKU: {product['sku']})",
                _format_attributes(product),
                f"![{product['sku']}]({image_url})",
                ""
            ])
        return "\n".join(response_parts)

    # Score all products against criteria
    scored: List[Tuple[int, Dict[str, Any], List[str]]] = []
    for candidate in catalog:
        score, reasons = _score_product(criteria, candidate)
        if score > 0:
            scored.append((score, candidate, reasons))

    # Sort by score and select top results
    scored.sort(key=lambda row: row[0], reverse=True)
    selected = scored[:min(max_results, len(scored))]

    if not selected:
        return (
            "No se encontraron productos que coincidan con los criterios especificados. "
            "Probá con criterios más amplios o consultá el catálogo completo."
        )

    response_parts = ["**Productos recomendados:**", ""]

    for index, (score, product, reasons) in enumerate(selected, start=1):
        image_url = f"{PRODUCT_ASSETS_BASE_URL}/images/{product['image_file']}"
        reason_text = "; ".join(reasons[:5]) if reasons else "atributos generales"
        
        response_parts.extend([
            f"**{index}. {product['product']}** (SKU: {product['sku']})",
            f"   - Por qué lo recomendamos: {reason_text}",
            _format_attributes(product),
            f"   ![{product['sku']}]({image_url})",
            ""
        ])

    return "\n".join(response_parts)

# Made with Bob
