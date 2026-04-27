import argparse
import json
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

# MediaWiki INSERT lines look like:
#   INSERT INTO `table` VALUES (v1,v2,...),(v1,v2,...),...;
# Values can be integers, quoted strings (with backslash escapes), or NULL.

def iter_insert_tuples(filepath: Path, table_name: str):
    """Yield lists of field strings from INSERT INTO statements in a SQL dump."""
    prefix = f"INSERT INTO `{table_name}` VALUES "
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith(prefix):
                continue
            data = line[len(prefix):]
            yield from _parse_tuples(data)


def _parse_tuples(data: str):
    """Parse all (v1,v2,...) tuples from DATA using a state machine."""
    i = 0
    n = len(data)
    while i < n:
        # Skip until '('
        while i < n and data[i] != "(":
            i += 1
        if i >= n:
            return
        i += 1  # skip '('

        # Collect fields until matching ')'
        fields: list[str] = []
        while i < n and data[i] != ")":
            if data[i] == "'":
                # Quoted string
                j = i + 1
                parts: list[str] = []
                while j < n:
                    if data[j] == "\\" and j + 1 < n:
                        parts.append(data[j + 1])
                        j += 2
                    elif data[j] == "'":
                        break
                    else:
                        parts.append(data[j])
                        j += 1
                fields.append("".join(parts))
                i = j + 1  # past closing quote
                # skip comma
                if i < n and data[i] == ",":
                    i += 1
            elif data[i] == ",":
                i += 1
            else:
                # Unquoted value (number, NULL)
                j = i
                while j < n and data[j] not in (",", ")"):
                    j += 1
                fields.append(data[i:j])
                i = j
                if i < n and data[i] == ",":
                    i += 1

        yield fields
        i += 1  # skip ')'

def parse_linktarget(sql_path: Path) -> dict[int, str]:
    """Return {lt_id: category_title} for category-namespace targets."""
    print("Pass 1: parsing linktarget …")
    t0 = time.time()
    lt_map: dict[int, str] = {}
    count = 0
    for fields in iter_insert_tuples(sql_path, "linktarget"):
        count += 1
        # lt_id, lt_namespace, lt_title
        if len(fields) < 3:
            continue
        ns = int(fields[1])
        if ns != 14:  # 14 = Category namespace
            continue
        lt_id = int(fields[0])
        title = fields[2].replace("_", " ")
        lt_map[lt_id] = title
    elapsed = time.time() - t0
    print(f"  → {len(lt_map):,} category targets found ({count:,} total rows) in {elapsed:.1f}s")
    return lt_map


def parse_page(sql_path: Path) -> tuple[dict[int, str], set[int], dict[int, str]]:
    """Return:
    - page_titles: {page_id: page_title} for namespace 0 (articles)
    - cat_page_ids: set of page_ids that are category pages (ns=14)
    - cat_id_to_title: {page_id: cat_title} for ns=14
    """
    print("Pass 2: parsing page …")
    t0 = time.time()
    page_titles: dict[int, str] = {}
    cat_page_ids: set[int] = set()
    cat_id_to_title: dict[int, str] = {}
    count = 0
    for fields in iter_insert_tuples(sql_path, "page"):
        count += 1
        # page_id, page_namespace, page_title, page_is_redirect, page_is_new,
        # page_random, page_touched, page_links_updated, page_latest, page_len, ...
        if len(fields) < 9:
            continue
        page_id = int(fields[0])
        ns = int(fields[1])
        title = fields[2].replace("_", " ")
        if ns == 0:
            page_titles[page_id] = title
        elif ns == 14:
            cat_page_ids.add(page_id)
            cat_id_to_title[page_id] = title
    elapsed = time.time() - t0
    print(f"  → {len(page_titles):,} articles, {len(cat_page_ids):,} categories ({count:,} total) in {elapsed:.1f}s")
    return page_titles, cat_page_ids, cat_id_to_title


def parse_categorylinks(
    sql_path: Path,
    lt_map: dict[int, str],
    cat_page_ids: set[int],
    cat_id_to_title: dict[int, str],
    page_titles: dict[int, str],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Return:
    - child_to_parents: {child_category: [parent_categories]}
    - article_cats: {article_title: [categories]}
    """
    print("Pass 3: parsing categorylinks …")
    t0 = time.time()
    child_to_parents: dict[str, list[str]] = defaultdict(list)
    article_cats: dict[str, list[str]] = defaultdict(list)
    count = 0
    skipped_target = 0
    for fields in iter_insert_tuples(sql_path, "categorylinks"):
        count += 1
        # cl_from, cl_sortkey, cl_timestamp, cl_sortkey_prefix,
        # cl_type, cl_collation_id, cl_target_id
        if len(fields) < 7:
            continue
        cl_from = int(fields[0])
        cl_type = fields[4]  # 'page', 'subcat', or 'file'
        cl_target_id = int(fields[6])

        # Resolve target category name
        parent_cat = lt_map.get(cl_target_id)
        if parent_cat is None:
            skipped_target += 1
            continue

        if cl_type == "subcat" and cl_from in cat_page_ids:
            child_name = cat_id_to_title.get(cl_from)
            if child_name:
                child_to_parents[child_name].append(parent_cat)
        elif cl_type == "page" and cl_from in page_titles:
            article_cats[page_titles[cl_from]].append(parent_cat)

        if count % 5_000_000 == 0:
            print(f"  … {count:,} rows processed")

    elapsed = time.time() - t0
    print(
        f"  → {len(child_to_parents):,} categories in hierarchy, "
        f"{len(article_cats):,} articles with categories "
        f"({count:,} total, {skipped_target:,} unresolved targets) in {elapsed:.1f}s"
    )
    return dict(child_to_parents), dict(article_cats)


def compute_depth(child_to_parents: dict[str, list[str]], root: str) -> dict[str, int]:
    """BFS from root downward. Returns {category: depth}."""
    print(f"Computing depth from root '{root}' …")
    t0 = time.time()

    # Build parent → children for BFS traversal
    parent_to_children: dict[str, list[str]] = defaultdict(list)
    for child, parents in child_to_parents.items():
        for p in parents:
            parent_to_children[p].append(child)

    depth: dict[str, int] = {root: 0}
    queue: deque[str] = deque([root])
    while queue:
        node = queue.popleft()
        d = depth[node]
        for child in parent_to_children.get(node, []):
            if child not in depth:
                depth[child] = d + 1
                queue.append(child)

    elapsed = time.time() - t0
    print(f"  → {len(depth):,} categories reachable from root in {elapsed:.1f}s")
    return depth


def main():
    parser = argparse.ArgumentParser(description="Build category graph from Wikimedia SQL dumps.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "categories",
        help="Directory containing the SQL dumps",
    )
    parser.add_argument(
        "--root",
        default="Artículos",
        help="Root category name (without 'Categoría:' prefix)",
    )
    args = parser.parse_args()

    data_dir: Path = args.data_dir

    # Find SQL files (glob for any date)
    lt_files = sorted(data_dir.glob("*-linktarget.sql"))
    page_files = sorted(data_dir.glob("*-page.sql"))
    cl_files = sorted(data_dir.glob("*-categorylinks.sql"))

    if not lt_files or not page_files or not cl_files:
        print("ERROR: Could not find all three SQL files in", data_dir)
        print("  Need: *-linktarget.sql, *-page.sql, *-categorylinks.sql")
        sys.exit(1)

    lt_path = lt_files[-1]
    page_path = page_files[-1]
    cl_path = cl_files[-1]
    print(f"Using:\n  linktarget: {lt_path.name}\n  page:       {page_path.name}\n  catlinks:   {cl_path.name}\n")

    # Parse
    lt_map = parse_linktarget(lt_path)
    page_titles, cat_page_ids, cat_id_to_title = parse_page(page_path)
    child_to_parents, article_cats = parse_categorylinks(
        cl_path, lt_map, cat_page_ids, cat_id_to_title, page_titles
    )

    # Free memory we no longer need
    del lt_map, cat_page_ids, cat_id_to_title, page_titles

    # Compute depth
    depth = compute_depth(child_to_parents, args.root)

    # Save outputs
    out_graph = data_dir / "category_graph.json"
    out_depth = data_dir / "category_depth.json"
    out_articles = data_dir / "article_categories.json"

    print(f"\nSaving {out_graph.name} …")
    with open(out_graph, "w", encoding="utf-8") as f:
        json.dump(child_to_parents, f, ensure_ascii=False)

    print(f"Saving {out_depth.name} …")
    with open(out_depth, "w", encoding="utf-8") as f:
        json.dump(depth, f, ensure_ascii=False)

    print(f"Saving {out_articles.name} …")
    with open(out_articles, "w", encoding="utf-8") as f:
        json.dump(article_cats, f, ensure_ascii=False)

    print(f"\nDone! Outputs in {data_dir}/")
    print(f"  category_graph.json:      {len(child_to_parents):,} categories (child → parents)")
    print(f"  category_depth.json:      {len(depth):,} categories with depth")
    print(f"  article_categories.json:  {len(article_cats):,} articles with categories")


if __name__ == "__main__":
    main()
