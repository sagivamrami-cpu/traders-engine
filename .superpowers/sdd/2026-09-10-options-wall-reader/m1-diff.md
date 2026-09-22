--- tests/tree_replay/test_optionswall.py (reviewed)
+++ tests/tree_replay/test_optionswall.py
@@ -33,10 +33,11 @@
         self.csv='time,close,src\n2026-09-09T14:45:00Z,2000,OANDA:XAUUSD\n'
         self.now=pd.Timestamp(now)
         self.calls=[]
     def list_reports(self):
         self.calls.append(('list',))
+        if isinstance(self.ids,Exception): raise self.ids
         return list(self.ids)
     def read_report(self,path):
         self.calls.append(('report',path))
         value=self.reports[path]
         if isinstance(value,Exception): raise value
@@ -182,5 +183,12 @@
 
 
 def test_decoded_wrong_report_shape_retains_original_uncaught_error():
     p=Artifacts(); p.reports['report-b.json']='[]'
     with pytest.raises(AttributeError): api().OptionsWallReader(p).status(SYMBOL)
+
+
+def test_listing_failure_propagates_before_later_ports():
+    p=Artifacts(); p.ids=OSError('listing unavailable')
+    with pytest.raises(OSError,match='listing unavailable'):
+        api().OptionsWallReader(p).status(SYMBOL)
+    assert p.calls==[('list',)]

