import os
import tempfile

os.environ["MEDTRACE_DATA_DIR"] = tempfile.mkdtemp()

from app.database import init_db
init_db()
