#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
# Copyright © 2020 Iain Lane <iain@orangesquash.org.uk>

import logging
import os
import ports
import subprocess

import setuppath  # noqa:F401
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus, StatusBase


class AAPrometheus(CharmBase):
    state = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        # -- standard hook observation
        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.start, self.on_start)
        self.framework.observe(self.on.stop, self.on_stop)
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        # -- initialize states --
        self.state.set_default(installed=False)
        self.state.set_default(configured=False)
        self.state.set_default(started=False)

    def _git_clone_or_pull(self):
        dest = "/srv/aa-prometheus"
        if not os.path.exists(dest):
            subprocess.check_call(
                [
                    "git",
                    "clone",
                    "https://github.com/iainlane/aa-prometheus.git",
                    "/srv/aa-prometheus",
                ]
            )
        else:
            subprocess.check_call(["git", "-C", dest, "pull"])

    def on_install(self, event):
        required_packages = ["git", "python3-pip"]

        self.unit.status = MaintenanceStatus("Installing charm software")
        subprocess.check_call(["apt", "-y", "install"] + required_packages)
        self._git_clone_or_pull()
        subprocess.check_call(
            [
                "pip3",
                "install",
                "--upgrade",
                "-r",
                "/srv/aa-prometheus/requirements.txt",
                "/srv/aa-prometheus",
            ]
        )
        subprocess.check_call(["systemctl", "daemon-reload"])
        self.unit.status = MaintenanceStatus("Install complete")
        logging.info("Install of software complete")
        self.state.installed = True

    def on_config_changed(self, event):
        if not self.state.installed:
            logging.warning(
                f"Config changed called before install complete, deferring event: {event.handle}."
            )
            self._defer_once(event)

            return

        if self.state.started:
            # Stop if necessary for reconfig
            logging.info(
                f"Stopping for configuration, event handle: {event.handle}."
            )
        # Configure the software
        logging.info("Configuring")
        self.state.configured = True

    def on_start(self, event):
        if not self.state.configured:
            logging.warning(
                "Start called before configuration complete, deferring event: {}".format(
                    event.handle
                )
            )
            self._defer_once(event)

            return
        self.unit.status = MaintenanceStatus("Starting charm software")
        subprocess.check_call(["systemctl", "start", "aa-prometheus.service"])
        ports.open_port("8000")
        self.unit.status = ActiveStatus("Unit is ready")
        self.state.started = True
        logging.info("Started")

    def on_stop(self, event):
        if not self.state.configured:
            logging.warning(
                "Start called before configuration complete, deferring event: {}".format(
                    event.handle
                )
            )
            self._defer_once(event)

            return
        self.unit.status = MaintenanceStatus("Stopping charm software")
        subprocess.check_call(["systemctl", "stop", "aa-prometheus.service"])
        ports.close_port("8000")
        self.unit.status = MaintenanceStatus("Unit stopped")
        self.state.started = False
        logging.info("Stopped")

    def _defer_once(self, event):
        """Defer the given event, but only once."""
        notice_count = 0
        handle = str(event.handle)

        for event_path, _, _ in self.framework._storage.notices(None):
            if event_path.startswith(handle.split("[")[0]):
                notice_count += 1
                logging.debug(
                    "Found event: {} x {}".format(event_path, notice_count)
                )

        if notice_count > 1:
            logging.debug(
                "Not deferring {} notice count of {}".format(
                    handle, notice_count
                )
            )
        else:
            logging.debug(
                "Deferring {} notice count of {}".format(handle, notice_count)
            )
            event.defer()


if __name__ == "__main__":
    from ops.main import main

    main(AAPrometheus)
