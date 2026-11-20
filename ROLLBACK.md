# Rollback Guide
Restore backup with:
cp app.py.bak app.py && python3 -m py_compile app.py && git add app.py && git commit -m "Rollback app.py" && git push origin main
