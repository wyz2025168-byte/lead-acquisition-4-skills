# Phase 0 结果

- 基线 commit：`0557c0d28331b82f4a147b6501c69b9367179aac`
- 保留 tag：`v3.0.0`
- 工作分支：`v4.0.0-rc.1`
- v3 发行包 SHA-256：`02454606c21d4859cc8c4c4ece739358725358b19172eb592f8a145ef19cafa2`
- v3 `SKILL.md` SHA-256：`b105d9e096033abd2d103bb25da9cbeab247afdf853087f492f65d45834ca8a8`
- `PACKAGE_MANIFEST.json` SHA-256：`ef68ef86e9641a60391da3994b02c08d5d29158a360a3cfe2a28b41505945329`
- `RELEASE_MANIFEST.json` SHA-256：`57ccb3b39cd95d534140f6c14c253eff27544f6969e45d97c0983d5011cdef22`

## 基线复现

- `python3 tools/validate-package.py`：14/14 PASS。
- `python3 skills/jw/scripts/jw_project.py doctor .`：PASS；版本 `3.0.0`，Schema `jw.project-state.v3`，七方法、38 项资格完整。
- 工作树在建立分支前无修改。
- 未修改 `v3.0.0` tag，未 commit、未 push、未发布。

## 基线裁决

v3 的安装、包完整性、隐私、方法注册、状态与哈希检查可复现。该结果只证明工程结构，不证明业务语义；Phase 1 将以 R01–R15 证明已知业务错误在 v3 中缺乏机器门禁。
