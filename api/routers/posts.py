from typing import List, Optional

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import get_current_user
from api.database import get_db
from api.schemas import SocialPost, CurrentUser

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=List[SocialPost])
def list_posts(
    source_id: Optional[int] = Query(None, description="Filtrer par source de données"),
    platform_id: Optional[int] = Query(None, description="Filtrer par plateforme"),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """Liste les publications, avec filtres optionnels et pagination — endpoint public (lecture générale)."""
    conditions, params = [], []
    if source_id is not None:
        conditions.append("source_id = ?")
        params.append(source_id)
    if platform_id is not None:
        conditions.append("platform_id = ?")
        params.append(platform_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT post_id, source_id, platform_id, external_post_id, text_content,
               published_at, likes, comments, shares, views
        FROM fact_social_post
        {where_clause}
        ORDER BY post_id
        LIMIT ? OFFSET ?
    """
    rows = db.execute(query, params + [limit, offset]).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]


@router.get("/{post_id}", response_model=SocialPost)
def get_post(post_id: int, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    row = db.execute(
        "SELECT post_id, source_id, platform_id, external_post_id, text_content, "
        "published_at, likes, comments, shares, views FROM fact_social_post WHERE post_id = ?",
        [post_id],
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Publication introuvable")
    columns = [d[0] for d in db.description]
    return dict(zip(columns, row))


@router.get("/scoped/me", response_model=List[SocialPost])
def list_my_scoped_posts(
    current_user: CurrentUser = Depends(get_current_user),
    limit: int = Query(50, le=500),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Démonstration des 2 niveaux d'admin du cahier des charges :
    - institution_admin -> voit toutes les sources
    - scoped_admin      -> ne voit que sa source (scope_source_id)
    """
    if current_user.role == "institution_admin":
        rows = db.execute(
            "SELECT post_id, source_id, platform_id, external_post_id, text_content, "
            "published_at, likes, comments, shares, views FROM fact_social_post ORDER BY post_id LIMIT ?",
            [limit],
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT post_id, source_id, platform_id, external_post_id, text_content, "
            "published_at, likes, comments, shares, views FROM fact_social_post "
            "WHERE source_id = ? ORDER BY post_id LIMIT ?",
            [current_user.scope_source_id, limit],
        ).fetchall()
    columns = [d[0] for d in db.description]
    return [dict(zip(columns, row)) for row in rows]
