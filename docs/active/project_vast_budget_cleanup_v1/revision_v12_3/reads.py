"""Provider whose read-only commands get the V12.2 bounded retry inside the caller's own timeout.

Mutations (create/start/stop/destroy/search) go straight to the unchanged V12 Provider.call, once.
No absolute deadline is added here: a retry never extends the caller's timeout, and a read after the
lease end (cleanup, STOP confirmation) is never refused by this layer.
"""
from read_retry import read_retry,TemporaryReadFailure,transient_stderr
from lifecycle import Provider

READS=(('show','instance'),('show','instances'),('show','volumes'),('show','invoices-v1'))


class ReadRetryProvider(Provider):
    def call(self,*args,json_result=True,timeout=15):
        if tuple(str(a) for a in args[:2]) not in READS:
            return super().call(*args,json_result=json_result,timeout=timeout)
        def perform(left):
            try:return super(ReadRetryProvider,self).call(*args,json_result=json_result,timeout=left)
            except OSError as error:
                if str(error)!='PROVIDER_COMMAND_FAILED':raise
                # The failed attempt's own preserved stderr decides; authentication/identity text never retries.
                if not transient_stderr((self.out/('%04d.stderr'%self.index)).read_bytes()):raise
                raise TemporaryReadFailure(str(error)) from error
        return read_retry(perform,tuple(str(a) for a in args),timeout=timeout,absolute_deadline=float('inf'),check=lambda:None)
