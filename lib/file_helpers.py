import os
def with_extension(filename, extension):
    base_filename = os.path.splitext(os.path.basename(filename))[0]
    return f"{base_filename}.{extension}"