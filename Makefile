tgz:
	rm dist/*.tar.gz || true
	./setup.py sdist 

upload-tgz: tgz
	./setup.py sdist upload
