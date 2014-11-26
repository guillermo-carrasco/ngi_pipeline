"""Provide ability to run bcbio-nextgen workflows.
"""
import collections
import os
import StringIO
import sys
import uuid

import tornado.gen
import tornado.web
import yaml

from ngi_pipeline.server import background


class RunPipeline(tornado.web.RequestHandler):
    """ Class to define pipeline running methods
    """
    def run_ngi_pipeline(args, callback=None):
        run_id = str(uuid.uuid1())
        def set_done(status, stdout, stderr, has_timed_out):
            self.application.runmonitor.set_status(run_id, "finished" if status == 0 else "failed")
        _run_local(args, set_done)
        app.runmonitor.set_status(run_id, "running")
        if callback:
            callback(run_id)
        else:
            return run_id

    def _run_local(args, callback):
        cmd = [os.path.join(os.path.dirname(sys.executable), "ngi_pipeline_start.py")] + args
        p = background.Subprocess(callback, timeout=-1, args=[str(x) for x in cmd])
        p.start()



##################################
#          Handlers              #
##################################
class FlowcellHandler(RunPipeline):
    """ Handler to manage flowcell processing

    GET /flowcell/(fc_dir)?restrict_to_projects=False&restrict_to_samples=False&restart_failed_jobs=False
    """
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, fc_dir):
        args = ['process', 'flowcell', fc_dir, self.get_argument('restrict_to_projects', False),
                self.get_argument('restrict_to_samples', False), self.get_argument('restart_failed_jobs', False)]
        run_id = yield tornado.gen.Task(self.run_ngi_pipeline, args)
        self.write(run_id)
        self.finish()


class TestHandler(tornado.web.RequestHandler):
    """ Execute a 'sleep' command
    """
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, secs):
        run_id = str(uuid.uuid1())
        def set_done(status, stdout, stderr, has_timed_out):
            self.application.runmonitor.set_status(run_id, "finished" if status == 0 else "failed")
        cmd = ['sleep', secs]
        p = background.Subprocess(set_done, timeout=-1, args=[str(x) for x in cmd])
        p.start()
        self.application.runmonitor.set_status(run_id, "running")

        self.write(run_id)



class StatusHandler(tornado.web.RequestHandler):
    def get(self):
        run_id = self.get_argument("run_id", None)
        if run_id is None:
            status = "server-up"
        else:
            status = self.application.runmonitor.get_status(run_id)
        self.write(status)
        self.finish()
