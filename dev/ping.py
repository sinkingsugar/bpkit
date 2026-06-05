import unreal
unreal.log(">>> channel ping from external python <<<")
print("ENGINE_VERSION", unreal.SystemLibrary.get_engine_version())
print("PROJECT_DIR", unreal.Paths.project_dir())
