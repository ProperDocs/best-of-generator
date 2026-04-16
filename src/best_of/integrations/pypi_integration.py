import json
import logging
import time

import pypistats
from addict import Dict

from best_of import utils
from best_of.integrations import libio_integration
from best_of.integrations.base_integration import BaseIntegration

log = logging.getLogger(__name__)


class PypiIntegration(BaseIntegration):
    @property
    def name(self) -> str:
        return "pypi"

    def update_project_info(self, project_info: Dict) -> None:
        if not project_info.pypi_id:
            return

        if not project_info.pypi_url:
            project_info.pypi_url = "https://pypi.org/project/" + project_info.pypi_id

        if libio_integration.is_activated():
            libio_integration.update_package_via_libio("pypi", project_info)

        self.update_via_pypistats(project_info)

    def generate_md_details(self, project: Dict, configuration: Dict) -> str:
        pypi_id = project.pypi_id
        if not pypi_id:
            return ""

        metrics_md = ""
        if project.pypi_monthly_downloads:
            if metrics_md:
                metrics_md += " · "
            metrics_md += (
                "📥 "
                + str(utils.simplify_number(project.pypi_monthly_downloads))
                + " / month"
            )

        if project.pypi_dependent_project_count:
            if metrics_md:
                metrics_md += " · "
            metrics_md += "📦 " + str(
                utils.simplify_number(project.pypi_dependent_project_count)
            )

        if project.pypi_latest_release_published_at:
            if metrics_md:
                metrics_md += " · "
            metrics_md += "⏱️ " + str(
                project.pypi_latest_release_published_at.strftime("%d.%m.%Y")
            )

        if metrics_md:
            metrics_md = " (" + metrics_md + ")"

        pypi_url = ""
        if project.pypi_url:
            pypi_url = project.pypi_url

        # https://badgen.net/#pypi

        # only show : if details are available
        separator = (
            ""
            if not configuration.generate_badges
            and not configuration.generate_install_hints
            else ":"
        )

        details_md = "- [PyPi](" + pypi_url + ")" + metrics_md + separator + "\n"

        if configuration.generate_install_hints:
            details_md += "\t```\n\tpip install {pypi_id}\n\t```\n"
        return details_md.format(pypi_id=pypi_id)

    def update_via_pypistats(self, project_info: Dict) -> None:
        # pypi stats limit is 30 per minute: https://github.com/crflynn/pypistats.org/issues/28#issuecomment-598417650
        # So, we try 10 times
        MAX_TRIES = 10
        for i in range(1, MAX_TRIES + 1):
            try:
                # get download count from pypi stats
                project_info.pypi_monthly_downloads = int(
                    json.loads(
                        pypistats.recent(project_info.pypi_id, "month", format="json")
                    )["data"]["last_month"]
                )

                # TODO use pepy api as fallback: https://api.pepy.tech/api/projects/lazydocs

                if not project_info.monthly_downloads:
                    project_info.monthly_downloads = 0

                project_info.monthly_downloads += int(
                    project_info.pypi_monthly_downloads
                )
                return
            except Exception:
                if i == MAX_TRIES:
                    raise
                sleep_time = 5 * i
                log.warning(
                    f"Failed request to pypistats. Sleep for {sleep_time} seconds and try again.",
                    exc_info=True
                )
                # wait for an increasing time
                time.sleep(sleep_time)
