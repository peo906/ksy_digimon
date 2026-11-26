---
name: github-sync
description: DigiPet 작업 폴더는 GitHub peo906/ksy_digimon에 올려 집과 회사에서 같이 씀. 메모리는 저장소 _claude_규칙/에도 복사본이 있음
metadata:
  node_type: memory
  type: reference
  originSessionId: 59d15955-f452-4a78-a2c0-ecf3ba7cd4ae
  modified: 2026-11-26T05:46:05.087Z
---

작업 폴더(Ver1_Mod_Kor)는 https://github.com/peo906/ksy_digimon (main)에 올라가 있다. 사용자가 집에서도 작업하려고 2026-11-26에 요청.

- 이 메모리 파일들의 복사본이 저장소 `_claude_규칙/memory/`에 있고, 루트 `CLAUDE.md`가 그것을 불러온다. 메모리를 고치면 그 복사본도 같이 고쳐야 집에서도 같은 규칙이 적용된다.
- `.gitignore`: `DigiPet.zip`, `evolution-atlas-deploy.tar.gz`, `__pycache__`, `*.bak`은 올리지 않는다.
- `evolution-atlas/`는 안에 자체 `.git`(원격 없음)이 있어서, 파일을 hash-object/update-index로 직접 넣었다. 그 폴더를 고친 뒤에는 `git add -A`가 안 잡을 수 있으니 확인 필요.
- 커밋·푸시는 사용자가 요청할 때만.

관련: [[digipet-sprite-pipeline]]
