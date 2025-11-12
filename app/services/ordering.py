from __future__ import annotations
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board_card import BoardCard
from app.models.board_list import BoardList

GAP = 65535


async def _rebalance_cards_in_list(db: AsyncSession, list_id: int) -> None:
    cards = (await db.execute(
        select(BoardCard).where(BoardCard.list_id == list_id).order_by(BoardCard.position.asc())
    )).scalars().all()
    for i, c in enumerate(cards, 1):
        c.position = i * GAP
    await db.flush()


async def _rebalance_lists_on_board(db: AsyncSession, board_id: int) -> None:
    lists = (await db.execute(
        select(BoardList).where(BoardList.board_id == board_id).order_by(BoardList.position.asc())
    )).scalars().all()
    for i, l in enumerate(lists, 1):
        l.position = i * GAP
    await db.flush()


async def new_card_position(
    db: AsyncSession,
    to_list_id: int,
    target_index: int,
    exclude_card_id: Optional[int] = None,
) -> int:
    """Izračunaj novu .position vrednost kartice koja ide u list 'to_list_id'
    na indeks 'target_index'. exclude_card_id služi da se kartica koja se pomera
    izbaci iz računice (pomeraš unutar iste liste)."""
    q = select(BoardCard).where(BoardCard.list_id == to_list_id).order_by(BoardCard.position.asc())
    cards = (await db.execute(q)).scalars().all()
    if exclude_card_id:
        cards = [c for c in cards if c.id != exclude_card_id]

    n = len(cards)
    if n == 0:
        return GAP

    if target_index <= 0:
        first = cards[0]
        if first.position > 1:
            return max(1, first.position // 2)
        await _rebalance_cards_in_list(db, to_list_id)
        return GAP  # nakon rebalansa, prvi će imati GAP, pa novi pre njega je GAP//2

    if target_index >= n:
        return cards[-1].position + GAP

    left = cards[target_index - 1].position
    right = cards[target_index].position
    if right - left > 1:
        return left + (right - left) // 2

    # nema prostora -> rebalance pa ponovo računaj
    await _rebalance_cards_in_list(db, to_list_id)
    cards = (await db.execute(
        select(BoardCard).where(BoardCard.list_id == to_list_id).order_by(BoardCard.position.asc())
    )).scalars().all()
    if exclude_card_id:
        cards = [c for c in cards if c.id != exclude_card_id]

    n = len(cards)
    if target_index <= 0:
        return max(1, cards[0].position // 2)
    if target_index >= n:
        return cards[-1].position + GAP
    return cards[target_index - 1].position + (cards[target_index].position - cards[target_index - 1].position) // 2


async def new_list_position(
    db: AsyncSession,
    board_id: int,
    target_index: int,
    exclude_list_id: Optional[int] = None,
) -> int:
    q = select(BoardList).where(BoardList.board_id == board_id).order_by(BoardList.position.asc())
    lists = (await db.execute(q)).scalars().all()
    if exclude_list_id:
        lists = [l for l in lists if l.id != exclude_list_id]

    n = len(lists)
    if n == 0:
        return GAP

    if target_index <= 0:
        first = lists[0]
        if first.position > 1:
            return max(1, first.position // 2)
        await _rebalance_lists_on_board(db, board_id)
        return GAP

    if target_index >= n:
        return lists[-1].position + GAP

    left = lists[target_index - 1].position
    right = lists[target_index].position
    if right - left > 1:
        return left + (right - left) // 2

    await _rebalance_lists_on_board(db, board_id)
    lists = (await db.execute(
        select(BoardList).where(BoardList.board_id == board_id).order_by(BoardList.position.asc())
    )).scalars().all()
    if exclude_list_id:
        lists = [l for l in lists if l.id != exclude_list_id]
    n = len(lists)
    if target_index <= 0:
        return max(1, lists[0].position // 2)
    if target_index >= n:
        return lists[-1].position + GAP
    return lists[target_index - 1].position + (lists[target_index].position - lists[target_index - 1].position) // 2
