from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 20
USER_AGENT = "Mozilla/5.0 HealthScanResearch/0.1"
URL_PATTERN = re.compile(r"https?://[^\s<>\"]+")
PRICE_PAGE_PATHS = (
    "/patients/billing/price-transparency",
    "/patients-visitors/billing-insurance/price-transparency",
    "/patient-resources/billing-insurance/price-transparency",
    "/patient-resources/patient-financial-resources/pricing-transparency",
    "/patients-visitors/paying-for-care/hospital-price-transparency",
    "/patients/billing-finance/comprehensive-hospital-charges",
    "/billing-insurance/price-transparency",
    "/price-transparency",
    "/standard-charges",
)


@dataclass(frozen=True)
class DiscoveryResult:
    source_url: str
    status_code: int
    content_type: str
    links: tuple[str, ...]
    raw_text: str


@dataclass(frozen=True)
class ProbeResult:
    url: str
    status_code: int
    content_type: str
    content_length: str
    final_url: str


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)


def cms_hpt_url(domain_or_url: str) -> str:
    parsed = urlparse(domain_or_url if "://" in domain_or_url else f"https://{domain_or_url}")
    if parsed.path.endswith("cms-hpt.txt"):
        return parsed.geturl()
    root = f"{parsed.scheme}://{parsed.netloc}"
    return urljoin(root, "/cms-hpt.txt")


def cms_hpt_candidates(domain_or_url: str) -> tuple[str, ...]:
    parsed = urlparse(domain_or_url if "://" in domain_or_url else f"https://{domain_or_url}")
    if parsed.path.endswith("cms-hpt.txt"):
        return (parsed.geturl(),)

    host = parsed.netloc
    candidates = [f"{parsed.scheme}://{host}/cms-hpt.txt"]
    if not host.startswith("www."):
        candidates.append(f"{parsed.scheme}://www.{host}/cms-hpt.txt")
    return tuple(dict.fromkeys(candidates))


def source_page_candidates(domain_or_url: str) -> tuple[str, ...]:
    parsed = urlparse(domain_or_url if "://" in domain_or_url else f"https://{domain_or_url}")
    if parsed.path and parsed.path not in ("", "/"):
        return (parsed.geturl(),)

    hosts = [parsed.netloc]
    if not parsed.netloc.startswith("www."):
        hosts.append(f"www.{parsed.netloc}")

    candidates = []
    for host in hosts:
        root = f"{parsed.scheme}://{host}"
        candidates.extend(urljoin(root, path) for path in PRICE_PAGE_PATHS)
    return tuple(dict.fromkeys(candidates))


def extract_links(body: str, base_url: str) -> tuple[str, ...]:
    links: list[str] = []
    links.extend(match.group(0).rstrip(".,);]") for match in URL_PATTERN.finditer(body))

    parser = _HrefParser()
    parser.feed(body)
    links.extend(urljoin(base_url, href) for href in parser.links)

    return tuple(dict.fromkeys(links))


def discover(domain_or_url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> DiscoveryResult:
    url = cms_hpt_url(domain_or_url)
    request = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=timeout) as response:
        body = response.read()
        content_type = response.headers.get("content-type", "")
        charset = response.headers.get_content_charset() or "utf-8"
        text = body.decode(charset, errors="replace")
        status = getattr(response, "status", 200)

    return DiscoveryResult(
        source_url=url,
        status_code=status,
        content_type=content_type,
        links=extract_links(text, url),
        raw_text=text,
    )


def discover_first_available(domain_or_url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> DiscoveryResult:
    last_error: Exception | None = None
    for url in cms_hpt_candidates(domain_or_url):
        try:
            return discover(url, timeout=timeout)
        except Exception as error:  # noqa: BLE001 - caller needs the final fetch failure context.
            last_error = error
    if last_error is None:
        raise ValueError(f"No cms-hpt.txt candidates for {domain_or_url!r}")
    raise last_error


def probe_url(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> ProbeResult:
    request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        response = urlopen(request, timeout=timeout)
    except Exception:
        request = Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"})
        response = urlopen(request, timeout=timeout)

    with response:
        return ProbeResult(
            url=url,
            status_code=getattr(response, "status", 200),
            content_type=response.headers.get("content-type", ""),
            content_length=response.headers.get("content-length", ""),
            final_url=response.geturl(),
        )


def likely_mrf_links(links: Iterable[str]) -> tuple[str, ...]:
    markers = ("standardcharges", "standard-charges", "mrfdownload", "pricing_files")
    extensions = (".csv", ".json", ".zip", ".gz", ".ashx")
    likely: list[str] = []
    for link in links:
        parsed = urlparse(link)
        haystack = f"{parsed.path}?{parsed.query}".lower()
        if any(marker in haystack for marker in markers) or any(ext in haystack for ext in extensions):
            likely.append(link)
    return tuple(likely)
