def test_gui_module_imports():
    import mocap.gui
    assert callable(mocap.gui.main)
