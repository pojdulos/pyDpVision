class Globals:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Globals, cls).__new__(cls, *args, **kwargs)
            cls._instance.mainApp = None
            cls._instance.mainWin = None
        return cls._instance
