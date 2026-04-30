@echo off
REM Survey what's actually in F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\repos\
REM and report which Demoncore subsystems are wired vs missing.

setlocal EnableExtensions EnableDelayedExpansion

set "REPOS=F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\repos"

echo.
echo === Demoncore Tool Inventory ===
echo Repos root: %REPOS%
echo.

if not exist "%REPOS%" (
  echo [x] repos dir not found at %REPOS%
  echo     Has the monorepo restructure completed?
  pause & exit /b 1
)

REM ---------------------------------------------------------------------------
echo --- Layer 5 ^(Hero Actors^) ---
call :probe "_visual\KawaiiPhysics"          "KawaiiPhysics"           "https://github.com/pafuhana1213/KawaiiPhysics"            "Layer 5: jiggle / secondary motion"
call :probe "_animation\ai4animationpy"      "AI4AnimationPy"          "https://github.com/sebastianstarke/AI4AnimationPy"        "Layer 5: neural locomotion (train -> ONNX -> NNE)"
call :probe "_voice\higgs-audio"             "Higgs Audio v2"          "https://github.com/EleutherAI/Higgs-Audio"                "Layer 5: voice cloning per NPC"
call :probe "_voice\F5-TTS"                  "F5-TTS"                   "https://github.com/SWivid/F5-TTS"                         "Layer 5: lightweight voice synth"
call :probe "_voice\bark"                    "Bark (Suno)"              "https://github.com/suno-ai/bark"                          "Layer 5: ambient voice / mob noises"
echo.

REM ---------------------------------------------------------------------------
echo --- Layer 3 ^(Mid Background^) ---
call :probe "_navmesh\Pathfinder"            "atom0s/Pathfinder"        "https://github.com/atom0s/Pathfinder"                     "Layer 3: extract collision geometry from FFXI .DATs"
call :probe "_navmesh\FFXI-NavMesh-Builder"  "FFXI-NavMesh-Builder"     "https://github.com/Windower/FFXI-NavMesh-Builder"         "Layer 3: Recast/Detour navmesh for LSB AI"
echo.

REM ---------------------------------------------------------------------------
echo --- Visual upscale + texture ---
call :probe "_visual\Real-ESRGAN"            "Real-ESRGAN"              "https://github.com/xinntao/Real-ESRGAN"                   "Layer 3: 4x texture upscale"
call :probe "_visual\ComfyUI"                "ComfyUI"                  "https://github.com/comfyanonymous/ComfyUI"                "Generated content: SD pipelines"
echo.

REM ---------------------------------------------------------------------------
echo --- AI orchestration ^(server side^) ---
call :probe "_agents\generative_agents"      "Stanford Generative Agents" "https://github.com/joonspk-research/generative_agents"  "NPC LLM-driven behavior"
call :probe "_combat_rl\PettingZoo"          "PettingZoo"               "https://github.com/Farama-Foundation/PettingZoo"          "Combat RL: multi-agent envs"
call :probe "_combat_rl\nmmo2"               "Neural MMO 2.0"           "https://github.com/NeuralMMO/environment"                 "Combat RL: persistent-world envs"
echo.

REM ---------------------------------------------------------------------------
echo --- Auth + economy ---
call :probe "_auth\discord-oauth2.py"        "Discord OAuth2 (Python)"  "https://github.com/treeben77/discord-oauth2.py"           "Auth: replace PlayOnline"
call :probe "_auth\discord-oauth2-example"   "Discord OAuth2 example"   "https://github.com/discord/discord-oauth2-example"        "Auth: official sample"
echo.

REM ---------------------------------------------------------------------------
echo --- Music ---
call :probe "_music\ACE-Step"                "ACE-Step v1.5"            "https://github.com/ace-step/ace-step"                     "Music gen: per-zone BGM"
echo.

REM ---------------------------------------------------------------------------
echo --- UE5 integration ---
call :probe "_ue\unreal-engine-mcp"          "Unreal Engine MCP"        "https://github.com/runreal/unreal-engine-mcp"             "UE5 control via MCP from chharbot"
echo.

REM ---------------------------------------------------------------------------
echo === Wiring status ===
echo.
echo The pull-and-retile pipeline:
echo   stage-monorepo\EXTRACT_BASTOK_FROM_RETAIL.bat   ^<- mesh + textures from retail
echo   stage-monorepo\UPSCALE_BASTOK_TEXTURES.bat       ^<- Real-ESRGAN x4
echo   stage-monorepo\ue5_scripts\bastok_import_extracted.py  ^<- import to UE5
echo.
echo The layered scene:
echo   stage-monorepo\ue5_scripts\bastok_layered_scene.py     ^<- film-style composition
echo.
echo The plugin install:
echo   stage-monorepo\INSTALL_DEMONCORE_PLUGINS.bat           ^<- enable KawaiiPhysics + LiveLink + NNE etc.
echo.
echo The blockout fast preview:
echo   stage-monorepo\RUN_BASTOK_BLOCKOUT.bat                 ^<- one-click preview
echo.

pause
endlocal
exit /b 0


REM =======================================================================
REM probe subroutine: %1 = relative path under repos\, %2 = display name,
REM                   %3 = clone URL, %4 = description
REM =======================================================================
:probe
set "REL=%~1"
set "NAME=%~2"
set "URL=%~3"
set "DESC=%~4"
if exist "%REPOS%\%REL%" (
  echo   [READY]   %NAME%
  echo            %DESC%
) else (
  echo   [MISSING] %NAME%
  echo            %DESC%
  echo            git clone %URL% "%REPOS%\%REL%"
)
exit /b 0
