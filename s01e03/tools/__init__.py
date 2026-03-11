from .packages import check_package, redirect_package

ALL_TOOLS = [check_package, redirect_package]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
