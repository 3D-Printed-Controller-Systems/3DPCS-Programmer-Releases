# 3DPCS packs

The packs the 3DPCS Controller Tool offers in its **Pack Manager**. The app reads `catalog.json` from this branch.

- **Add a pack:** drop the `.3dpack` into `packs/` and push. The catalog rebuilds itself (Actions, about 20 seconds).
- **Update a pack:** replace the file with the new version (raise `version` in its manifest) and push. Players with the old version see Update.
- **Flavor text:** `notes.json` holds one short line per pack id, shown under the name ("Requires LEDs").
- **Can't run together:** `rules.json` lists pairs of packs whose mods can never be on together in one profile. The app enforces it.
- **Retire a pack:** delete the file. It stops being offered; copies people have keep working.

A mod is official only when its exact file is in this catalog, so check a mod before adding it
(`python3 tools/mods/tools/pcspack.py check <pack>` in the dev repo). Color packs people make themselves don't go here.
