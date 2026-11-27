"""Deterministic panel numbering and verified cross-image panel re-identification."""
from hashlib import sha1
from ..association.iou import box_iou
from .coordinate_transform import transform_bbox, transform_polygon


def assign_panel_identities(panels, image_id=None, image_scope=None):
    """Assign deterministic image-local IDs and structured grid labels without inventing global IDs."""
    scope = image_scope or (str(image_id) if image_id else None)
    ordered = sorted(
        panels,
        key=lambda p: (
            p.get("region_id") or 1,
            p.get("row_id") or 0,
            p.get("column_id") or 0,
        ),
    )
    for seq, panel in enumerate(ordered, start=1):
        row_num = int(panel.get("row_id") or 1)
        col_num = int(panel.get("column_id") or seq)
        grid_row = int(panel.get("grid_row_id") or row_num)
        grid_col = int(panel.get("grid_column_id") or col_num)
        local_code = f"R{row_num:02d}C{col_num:02d}"
        panel["panel_id"] = f"IMG{scope}-{local_code}" if scope else local_code
        panel["display_id"] = f"P-{seq:05d}"
        panel["row_label"] = f"R-{grid_row:02d}"
        panel["column_label"] = f"C-{grid_col:02d}"
        panel["identity_scope"] = "image_local"
        panel["site_panel_id"] = None
        if image_id is not None:
            panel["image_id"] = image_id
    return ordered


def _union_find_components(nodes, edges):
    parent = {node: node for node in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    for a, b in edges:
        union(a, b)

    groups = {}
    for node in nodes:
        groups.setdefault(find(node), []).append(node)
    return list(groups.values())


def reidentify_panels_across_images(panels_by_image, pairwise_registrations, iou_threshold=0.35):
    """Assign shared site_panel_id values ONLY across images with verified REGISTERED transforms.

    pairwise_registrations is an iterable of dicts with:
      - source_image_id (or movingImageId)
      - target_image_id (or referenceImageId)
      - status == "REGISTERED"
      - transform (3x3 homography mapping source -> target pixels)
    """
    panel_lookup = {}
    for img_id, panels in panels_by_image.items():
        for idx, p in enumerate(panels):
            p.setdefault("site_panel_id", None)
            p.setdefault("identity_scope", "image_local")
            key = (img_id, p.get("panel_id") or f"idx-{idx}")
            panel_lookup[key] = p

    verified_pairs = [
        reg for reg in (pairwise_registrations or [])
        if reg.get("status") == "REGISTERED" and reg.get("transform")
    ]
    if not verified_pairs:
        return {"status": "UNVERIFIED_IMAGE_LOCAL", "matched_pairs": 0, "site_panel_count": 0}

    edges = []
    matched_pair_count = 0
    for reg in verified_pairs:
        src_id = reg.get("source_image_id") or reg.get("movingImageId")
        dst_id = reg.get("target_image_id") or reg.get("referenceImageId")
        matrix = reg["transform"]
        src_panels = panels_by_image.get(src_id, [])
        dst_panels = panels_by_image.get(dst_id, [])
        if not src_panels or not dst_panels:
            continue
        matched_pair_count += 1
        used_dst = set()
        for s_idx, sp in enumerate(src_panels):
            mapped_box = transform_bbox(sp["bbox"], matrix)
            if mapped_box is None:
                continue
            best_score = 0.0
            best_key = None
            for d_idx, dp in enumerate(dst_panels):
                d_key = (dst_id, dp.get("panel_id") or f"idx-{d_idx}")
                if d_key in used_dst:
                    continue
                score = box_iou(mapped_box, dp["bbox"])
                if score > best_score:
                    best_score = score
                    best_key = d_key
            if best_key is not None and best_score >= iou_threshold:
                s_key = (src_id, sp.get("panel_id") or f"idx-{s_idx}")
                edges.append((s_key, best_key))
                used_dst.add(best_key)

    if not edges:
        return {"status": "UNVERIFIED_IMAGE_LOCAL", "matched_pairs": matched_pair_count, "site_panel_count": 0}

    components = _union_find_components(sorted(panel_lookup.keys()), edges)
    components.sort(key=lambda comp: min(comp))
    site_count = 0
    for comp in components:
        if len(comp) < 2:
            continue
        site_count += 1
        digest = sha1("|".join(f"{i}:{pid}" for i, pid in sorted(comp)).encode("utf-8")).hexdigest()[:6].upper()
        site_id = f"SITE-{site_count:04d}-{digest}"
        for key in comp:
            panel_lookup[key]["site_panel_id"] = site_id
            panel_lookup[key]["identity_scope"] = "site_registered"

    return {
        "status": "VERIFIED_REGISTERED" if site_count > 0 else "UNVERIFIED_IMAGE_LOCAL",
        "matched_pairs": matched_pair_count,
        "site_panel_count": site_count,
    }
