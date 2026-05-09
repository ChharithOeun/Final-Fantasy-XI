"""Player correspondence — long letters between players.

The /tell command is fine for "are you online?" but
players who travel together over years deserve a
proper letter system. This module manages LETTERS:
multi-paragraph messages, optional attachments
(items routed via delivery_box), threading (replies
chain to a parent), and READING STATE per recipient.

A letter has:
    letter_id, author_id, recipients (1+), subject,
    body, parent_letter_id (for replies), sent_day,
    attachment_item_ids (delivery_box keys).

Per-recipient state:
    UNREAD, READ, ARCHIVED, DELETED.

Public surface
--------------
    LetterState enum
    Letter dataclass (frozen)
    PlayerCorrespondenceSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LetterState(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclasses.dataclass(frozen=True)
class Letter:
    letter_id: str
    author_id: str
    recipients: tuple[str, ...]
    subject: str
    body: str
    parent_letter_id: t.Optional[str]
    attachment_item_ids: tuple[str, ...]
    sent_day: int


@dataclasses.dataclass
class _LState:
    spec: Letter
    states: dict[str, LetterState] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerCorrespondenceSystem:
    _letters: dict[str, _LState] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def send_letter(
        self, *, author_id: str,
        recipients: t.Sequence[str], subject: str,
        body: str,
        parent_letter_id: t.Optional[str] = None,
        attachment_item_ids: t.Sequence[str] = (),
        sent_day: int = 0,
    ) -> t.Optional[str]:
        if not author_id:
            return None
        if not recipients:
            return None
        if author_id in recipients:
            return None
        if len(set(recipients)) != len(recipients):
            return None
        if not subject or not body:
            return None
        if sent_day < 0:
            return None
        if (parent_letter_id is not None
                and parent_letter_id
                not in self._letters):
            return None
        lid = f"letter_{self._next_id}"
        self._next_id += 1
        spec = Letter(
            letter_id=lid, author_id=author_id,
            recipients=tuple(recipients),
            subject=subject, body=body,
            parent_letter_id=parent_letter_id,
            attachment_item_ids=tuple(
                attachment_item_ids,
            ),
            sent_day=sent_day,
        )
        self._letters[lid] = _LState(
            spec=spec,
            states={r: LetterState.UNREAD
                    for r in recipients},
        )
        return lid

    def mark_read(
        self, *, letter_id: str, recipient_id: str,
    ) -> bool:
        if letter_id not in self._letters:
            return False
        st = self._letters[letter_id]
        if recipient_id not in st.states:
            return False
        cur = st.states[recipient_id]
        if cur in (LetterState.ARCHIVED,
                   LetterState.DELETED):
            return False
        if cur == LetterState.READ:
            return False
        st.states[recipient_id] = LetterState.READ
        return True

    def archive(
        self, *, letter_id: str, recipient_id: str,
    ) -> bool:
        if letter_id not in self._letters:
            return False
        st = self._letters[letter_id]
        if recipient_id not in st.states:
            return False
        if st.states[recipient_id] == (
            LetterState.DELETED
        ):
            return False
        st.states[recipient_id] = (
            LetterState.ARCHIVED
        )
        return True

    def delete(
        self, *, letter_id: str, recipient_id: str,
    ) -> bool:
        if letter_id not in self._letters:
            return False
        st = self._letters[letter_id]
        if recipient_id not in st.states:
            return False
        if st.states[recipient_id] == (
            LetterState.DELETED
        ):
            return False
        st.states[recipient_id] = LetterState.DELETED
        return True

    def state_for(
        self, *, letter_id: str, recipient_id: str,
    ) -> t.Optional[LetterState]:
        if letter_id not in self._letters:
            return None
        return self._letters[letter_id].states.get(
            recipient_id,
        )

    def inbox(
        self, *, recipient_id: str,
        include_archived: bool = False,
    ) -> list[Letter]:
        out: list[Letter] = []
        for st in self._letters.values():
            s = st.states.get(recipient_id)
            if s is None:
                continue
            if s == LetterState.DELETED:
                continue
            if (s == LetterState.ARCHIVED
                    and not include_archived):
                continue
            out.append(st.spec)
        return sorted(
            out, key=lambda l: l.sent_day,
        )

    def thread_of(
        self, *, letter_id: str,
    ) -> list[Letter]:
        """Walk parent chain back to root."""
        if letter_id not in self._letters:
            return []
        chain: list[Letter] = []
        cur: t.Optional[str] = letter_id
        seen: set[str] = set()
        while cur is not None and cur not in seen:
            seen.add(cur)
            spec = self._letters[cur].spec
            chain.append(spec)
            cur = spec.parent_letter_id
        chain.reverse()
        return chain

    def replies_to(
        self, *, letter_id: str,
    ) -> list[Letter]:
        return [
            st.spec for st in self._letters.values()
            if st.spec.parent_letter_id == letter_id
        ]

    def letter(
        self, *, letter_id: str,
    ) -> t.Optional[Letter]:
        if letter_id not in self._letters:
            return None
        return self._letters[letter_id].spec

    def unread_count(
        self, *, recipient_id: str,
    ) -> int:
        return sum(
            1 for st in self._letters.values()
            if st.states.get(recipient_id)
            == LetterState.UNREAD
        )


__all__ = [
    "LetterState", "Letter",
    "PlayerCorrespondenceSystem",
]
