# SHBC-Gesture11 正式发布流程

本交付以现有三组件发布目录为基础：dataset、realtime_recognition、cat_control。不是完整训练复现仓库；训练实验代码仍在工作区的“代码”目录，不能声称本包包含论文全部训练实验。

## 1. 交付文件

- `SHBC-Gesture11-v1.0.0-repository.zip`：解压后将 SHBC-Gesture11 目录作为 Git 仓库根目录。含元数据、固定划分、下载/校验程序、两个应用的模型和依赖、第三方资产说明、引用文件、论文图稿。
- `../dataset_release/archives/`：20 个原始 JPEG 分卷、manifest.json、SHA256SUMS.txt，约 36.75 GB。已存在的分卷不重复压缩；其完整清单与实际校验结果见本交付 verification_report.json。
- `figures/`：图3、旧版编号图7，各有 SVG、PDF、PNG。
- `build_publication.py`：图稿和仓库包的重建源码；依赖 Pillow、reportlab。

## 2. 发布元信息

默认目标为 `ShaoyunZong/SHBC-Gesture11`，标签 `v1.0.0`。若改变，需同步 README、CITATION.cff、下载命令。

现有 LICENSE_PENDING.md 尚未提供最终许可证或参与者授权证据。本交付保留其状态，不擅自替数据所有者选择许可证。公开前请完成该文件列出的真实授权事项，并分别写入代码许可证、数据许可证、模型许可/第三方声明。CITATION.cff 的 `LicenseRef-Pending` 同步替换为实际数据许可；`date-released` 填实际公开日期，不能沿用旧包中尚未发生的发布日期。作者姓名与顺序请核对。

## 3. 本地准备

安装 Git、GitHub CLI，以及 Python 3.10–3.12。以下 PowerShell 命令在解压后的 SHBC-Gesture11 根目录执行。先运行 `gh auth login` 完成自己的 GitHub 登录。

```powershell
git init -b main
git add .
git diff --cached --stat
git commit -m "Release SHBC-Gesture11 dataset metadata and realtime applications"
gh repo create ShaoyunZong/SHBC-Gesture11 --public --source . --remote origin --push
```

如果目标仓库已经存在，不运行 `gh repo create`；先 clone 已有仓库，将交付文件复制进去，审阅差异后提交并 push。不要覆盖远端历史。

帧分卷被 .gitignore 排除，不要使用 `git add -f` 强行放入 Git 历史。GitHub 单个 Release 附件必须小于 2 GiB，现有 20 分卷按此限制拆分。

## 4. 创建草稿、上传全部附件

将下方目录替换为本机实际的 dataset_release/archives 绝对路径。20 个 ZIP 逐个上传，某个中断时重试该文件即可。

```powershell
$archiveDir = 'C:\Users\宗少云\Desktop\zsy-file\动态手势\动态手势\dataset_release\archives'
git tag -a v1.0.0 -m "SHBC-Gesture11 v1.0.0"
git push origin v1.0.0
gh release create v1.0.0 --repo ShaoyunZong/SHBC-Gesture11 --verify-tag --draft --title "SHBC-Gesture11 v1.0.0" --notes-file RELEASE_NOTES.md
Get-ChildItem -LiteralPath $archiveDir -Filter '*.zip' | Sort-Object Name | ForEach-Object {
    gh release upload v1.0.0 $_.FullName --repo ShaoyunZong/SHBC-Gesture11
    if ($LASTEXITCODE -ne 0) { throw "Upload failed: $($_.Name)" }
}
gh release upload v1.0.0 "$archiveDir\manifest.json" "$archiveDir\SHA256SUMS.txt" --repo ShaoyunZong/SHBC-Gesture11
gh release view v1.0.0 --repo ShaoyunZong/SHBC-Gesture11 --json assets
```

可另外上传仓库 ZIP 和本次图稿。首次正式公开前核对草稿中 20 个 ZIP 名称和字节数均与 dataset/release_manifest.json 一致。若替换已有附件，确认对象后才对该附件使用 `--clobber`。

## 5. 公开与下载验证

授权、许可证、附件核对完成后执行：

```powershell
gh release edit v1.0.0 --repo ShaoyunZong/SHBC-Gesture11 --draft=false
python dataset/scripts/download_dataset.py --repo ShaoyunZong/SHBC-Gesture11 --tag v1.0.0 --extract
python dataset/scripts/verify_dataset.py --check-frames
```

建议在新目录 clone 后完成下载与校验，排除本地旧数据掩盖缺失。首次校验需读约 36.75 GB 数据，请预留下载、分卷和解压空间。训练必须沿用视频级 split，禁止把帧随机混入训练和测试。

## 6. Linux 实机验证

参照根 README 分别安装两个应用依赖，运行 `recognize.py --camera 0` 与 `cat_control.py --camera 0 --open-browser`。确认镜像、无手输出 else、stop 保持、重新运动解除门控和浏览器预览正常。当前交付环境没有摄像头及 PyTorch，静态检查不能替代这一实机验证。

## 7. 论文插图替换

图3采用 Figure3_KMD_Transformer；图7采用 Figure7_Realtime_Control。优先插入 SVG 或 PDF，Word 不接受时使用 PNG，避免截图后再次压缩。

本次按用户确认采用旧版图7编号。v4 原文中图7是实时推理示例、流程图是图8，且存在“图78”误写：若采用本次图7，需在最终排版时统一调整该处图注和正文引用，避免两个图7。本交付没有覆盖任何论文版本。

## 官方依据

- [GitHub Release 附件限制](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [gh release create](https://cli.github.com/manual/gh_release_create)
- [gh release upload](https://cli.github.com/manual/gh_release_upload)
