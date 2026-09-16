--- tests/tree_replay/test_pattern_readers.py (reviewed)
+++ tests/tree_replay/test_pattern_readers.py
@@ -201,10 +201,20 @@
     f.iloc[10]=[100.,103.,99.,102.,3.]
     p=Frames({('X','5m',2):f})
     assert api('brinks').BrinksReader(p).today_box('X').open_vectors_inside==1
 
 
+def test_brinks_vector_input_error_is_unknown_not_zero():
+    f=frame(n=8,start='2026-09-09 14:00Z')
+    f['volume']='bad'
+    p=Frames({('X','5m',2):f})
+    box=api('brinks').BrinksReader(p).today_box('X')
+    assert box is not None and (box.hi,box.lo,box.close)==(101.,99.,100.)
+    assert box.open_vectors_inside is None
+    assert p.calls==[('clock',),('X','5m',2)]
+
+
 def rvc_frame(inverse=False,close=102.,upper=1.,lower=1.):
     f=frame(n=33)
     f.iloc[30]=[102.,103.,99.,100.,3.]
     f.iloc[31]=[100.,max(100.,close)+upper,100.-lower,close,10.]
     f.iloc[32]=[102.,103.,99.,100.,100.]  # opposite forming vector is ignored

