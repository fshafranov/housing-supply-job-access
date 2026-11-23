"""
fetch.py
Stage:      utils (shared by collection scripts)
Purpose:    Streamed HTTP download with retries; writes to a .part file and renames, so an
            interrupted download never leaves a truncated file under its final name.
"""
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500 or exc.response.status_code == 429
    return isinstance(exc, httpx.TransportError)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, max=60),
       retry=retry_if_exception(_retryable), reraise=True)
def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, timeout=300, follow_redirects=True,
                      headers={"User-Agent": "research-script"}) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
    tmp.replace(dest)
