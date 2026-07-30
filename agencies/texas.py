from .base import build_state

# Starter set -- confirmed against agency self-reported sites / Wikipedia
# infoboxes, Jul 2026. Smaller and less exhaustively audited than the
# Louisiana list; exists mainly to prove out the plugin architecture.
# Expand freely -- this is just a normal Python dict, same shape as
# every other state module.
RAW = {
    "01": ("Department of Public Safety", "site:dps.texas.gov filetype:pdf"),
    "02": ("Commission on Environmental Quality", "site:tceq.texas.gov filetype:pdf"),
    "03": ("Department of Transportation", "site:txdot.gov filetype:pdf"),
    "04": ("Commission on Law Enforcement", "site:tcole.texas.gov filetype:pdf"),
    "05": ("Health and Human Services Commission", "site:hhs.texas.gov filetype:pdf"),
    "06": ("Workforce Commission", "site:twc.texas.gov filetype:pdf"),
    "07": ("Office of the Attorney General", "site:texasattorneygeneral.gov filetype:pdf"),
    "08": ("Secretary of State", "site:sos.state.tx.us filetype:pdf"),
    "09": ("Education Agency", "site:tea.texas.gov filetype:pdf"),
    "10": ("Comptroller of Public Accounts", "site:comptroller.texas.gov filetype:pdf"),
}

STATE = build_state("TX", "Texas", RAW)
