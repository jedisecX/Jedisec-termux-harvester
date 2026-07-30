from .base import build_state

# Starter set -- confirmed domains only, Jul 2026. Same caveat as texas.py:
# small on purpose, meant to demonstrate the plugin pattern rather than
# be an exhaustive agency index yet.
RAW = {
    "01": ("Department of Transportation", "site:mdot.ms.gov filetype:pdf"),
    "02": ("Secretary of State", "site:sos.ms.gov filetype:pdf"),
    "03": ("Department of Wildlife, Fisheries, and Parks", "site:mdwfp.com filetype:pdf"),
    "04": ("Department of Archives and History", "site:mdah.ms.gov filetype:pdf"),
    "05": ("Department of Environmental Quality", "site:mdeq.ms.gov filetype:pdf"),
    "06": ("Library Commission", "site:mlc.lib.ms.us filetype:pdf"),
}

STATE = build_state("MS", "Mississippi", RAW)
