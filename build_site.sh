#!/bin/bash

# Build a repository of Stash plugins and scrapers
# Outputs to _site with the following structure:
# index.yml (plugins)
# scrapers.yml (scrapers)
# <plugin_id>.zip
# <scraper_id>.zip

outdir="$1"
if [ -z "$outdir" ]; then
    outdir="_site"
fi

rm -rf "$outdir"
mkdir -p "$outdir"

buildPlugin() 
{
    f=$1
    indexfile=$2  # Pass which index file to write to

    if grep -q "^#pkgignore" "$f"; then
        return
    fi
    
    # get the plugin id from the directory
    dir=$(dirname "$f")
    plugin_id=$(basename "$f" .yml)

    echo "Processing $plugin_id"

    # create a directory for the version
    version=$(git log -n 1 --pretty=format:%h -- "$dir"/*)
    updated=$(TZ=UTC0 git log -n 1 --date="format-local:%F %T" --pretty=format:%ad -- "$dir"/*)
    
    # create the zip file
    zipfile=$(realpath "$outdir/$plugin_id.zip")
    
    pushd "$dir" > /dev/null
    zip -r "$zipfile" . > /dev/null
    popd > /dev/null

    name=$(grep "^name:" "$f" | head -n 1 | cut -d' ' -f2- | sed -e 's/\r//' -e 's/^"\(.*\)"$/\1/')
    description=$(grep "^description:" "$f" | head -n 1 | cut -d' ' -f2- | sed -e 's/\r//' -e 's/^"\(.*\)"$/\1/')
    ymlVersion=$(grep "^version:" "$f" | head -n 1 | cut -d' ' -f2- | sed -e 's/^"\(.*\)"$/\1/')
    version="$ymlVersion-$version"
    # set IFS
    IFS=$'\n' dep=$(grep "^# requires:" "$f" | cut -c 13- | sed -e 's/\r//')

    # write to spec index
    echo "- id: $plugin_id
  name: $name
  metadata:
    description: $description
  version: $version
  date: $updated
  path: $plugin_id.zip
  sha256: $(sha256sum "$zipfile" | cut -d' ' -f1)" >> "$indexfile"

    # handle dependencies
    if [ ! -z "$dep" ]; then
        echo "  requires:" >> "$indexfile"
        for d in ${dep//,/ }; do
            echo "    - $d" >> "$indexfile"
        done
    fi

    echo "" >> "$indexfile"
}

find ./plugins -mindepth 1 -name *.yml | while read file; do
    buildPlugin "$file" "$outdir/index.yml"
done

find ./scrapers -mindepth 1 -maxdepth 2 -name *.yml | while read file; do
    buildPlugin "$file" "$outdir/scrapers.yml"
done
