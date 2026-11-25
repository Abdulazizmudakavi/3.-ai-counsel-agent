"""The only module allowed to send mail.

Prototype rule (team plan, Abdul): the send step exists but is hard-disabled. The switch is a
code constant, not an environment variable or database setting, so nothing in the running app
can turn it on. Changing it needs a pull request approved by Sana, Arina, Abdul and the advocate.
"""

from __future__ import annotations

from typing import Final

from counsel.contracts import DraftReply

SEND_ENABLED: Final[bool] = False


class SendDisabledError(RuntimeError):
    pass


def send_approved_draft(draft: DraftReply, approval_token: str) -> None:
    if not SEND_ENABLED:
        raise SendDisabledError("Sending is disabled in the prototype (L0 shadow mode).")
    raise NotImplementedError("Send path is built after the L1 go/no-go.")
