class ExcelFileError(Exception):
    """Base exception for excel file stuffs"""
    pass

class ExcelFileInvalidFormatError(ExcelFileError):
    """The file is not in supported excel file formats"""
    pass

class ExcelFileReadError(ExcelFileError):
    """Cannot read the given excel file"""
    pass
