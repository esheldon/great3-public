# rachel's code is not a library, we hae to copy it somewhere

prefix=~/exports/great3-public-work

default:

copy :
	@echo "rsyncing to $(prefix)"
	@if [ ! -e $(prefix) ]; then \
		echo Creating directory $(prefix); \
		mkdir -p $(prefix); \
	fi
	rsync -av \
		--exclude "*svn*" \
		--exclude "*git*" \
		--exclude "*swp" \
		--exclude "*~" \
		--exclude "*pyc" ./ $(prefix)/

