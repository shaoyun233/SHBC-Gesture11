# 发布到 shaoyun233/SHBC-Gesture11

你的仓库已确定为：https://github.com/shaoyun233/SHBC-Gesture11

本说明适用于本次更新后的完整包。不要再使用之前写有 ShaoyunZong 地址的旧包。

## 一、解压并确认目录

```text
SHBC-Gesture11-Full-Release/
  先读我_发布流程.md
  repository/SHBC-Gesture11/    上传到仓库代码页
  release-assets/              上传到 Release 附件区
  figures/                    图3和图7
  verification_report.json
  图稿生成源码.py
```

完整包约36.8 GB。外层ZIP是本地交付包，不上传GitHub；解压后分别上传上述两个目录中的内容。若已解压旧完整包，可以仅用新的小仓库ZIP替换 repository/SHBC-Gesture11，20个数据ZIP保持不变。

## 二、许可证已经填写

- 原创程序代码、配套文档、两个应用的KMD模型权重：MIT（根目录 LICENSE）。
- 图像帧、数据元信息、类别说明及固定划分：CC BY 4.0（dataset/LICENSE.md）。
- 本次原创论文图稿：CC BY 4.0（paper/figures/LICENSE.md）。
- 第三方软件、MediaPipe模型和三维猫模型：保留原许可及署名，参见 THIRD_PARTY_NOTICES.md。
- 原来的 LICENSE_PENDING.md 已替换为 LICENSING.md，记录你已确认授权、隐私和第三方权利核查完成，并写明联系及删除请求方式。

MIT和CC BY 4.0允许商业使用；CC BY 4.0要求署名、标注修改和提供许可链接。许可证适用范围不含论文正文。CITATION.cff 已改为正确地址与数据许可，实际发布日期请在公开当天填写。

## 三、上传或更新仓库文件

1. 登录GitHub，打开 https://github.com/shaoyun233/SHBC-Gesture11 。这是已有仓库，不用再创建同名仓库。
2. 点击“Add file”→“Upload files”。如果仓库为空，点页面中的“uploading an existing file”。
3. 将 `repository/SHBC-Gesture11/` **里面的所有文件和子文件夹**拖入上传区域。不要把外层SHBC-Gesture11文件夹整体套在仓库顶层。
4. 等全部上传完成，提交说明写 `Prepare SHBC-Gesture11 v1.0.0 release`，点击“Commit changes”（若界面要求分支/PR，按其提示创建并合并）。
5. 确认仓库顶层直接出现 README.md、LICENSE、LICENSING.md、CITATION.cff、dataset、realtime_recognition、cat_control、paper 等。确保 `.gitignore` 也上传。
6. 如果之前上传过 `LICENSE_PENDING.md`，在GitHub打开该文件，通过菜单“Delete file”删除并提交。网页上传新文件不会自动删除旧文件。此后以 LICENSING.md 为准。

仓库内容已检查：每个文件小于25 MiB，总文件数少于100，可以网页上传。`release-assets/` 里的分卷不要放进仓库代码页。

## 四、创建v1.0.0 Release并上传数据

1. 打开 https://github.com/shaoyun233/SHBC-Gesture11/releases/new 。
2. Tag选择或新建 `v1.0.0`，Target选包含最新上传文件的默认分支（通常是main）。
3. Release title填 `SHBC-Gesture11 v1.0.0`。
4. 将仓库根目录 `RELEASE_NOTES.md` 的内容复制到说明框。
5. 附件区域上传 `release-assets/` 里的20个ZIP，以及 `manifest.json`、`SHA256SUMS.txt`，共22个附件。保持原文件名。
6. 可先点击“Save draft”保存；分卷上传较慢时逐个或分批上传，确认全部完成。
7. 确认ZIP从 `01-of-20` 连续到 `20-of-20`，无缺号；20个ZIP合计36,748,893,112字节。
8. 正式版不勾选“This is a pre-release”，可勾选“Set as latest release”，点击“Publish release”。

如果已经有v1.0.0草稿，直接编辑已有草稿。若v1.0.0已公开，先查看其附件和目标提交；不要重复创建同名Release。若已启用不可变Release，已发布附件和标签不能更改，应使用新版本，并同步下载器默认tag与文档中的版本号。

每个Release附件必须小于2 GiB，现有20个分卷均符合。不要上传36.8 GB外层完整ZIP。若希望提供独立的程序下载，可以额外上传本次约18 MB的 `SHBC-Gesture11-v1.0.0-repository.zip`。

## 五、确认公众可访问

1. 仓库需为Public。若为Private，可在Settings→General→Danger Zone→Change repository visibility中改为Public。
2. 退出登录或打开浏览器无痕窗口，检查仓库和Release页面：
   - https://github.com/shaoyun233/SHBC-Gesture11
   - https://github.com/shaoyun233/SHBC-Gesture11/releases/tag/v1.0.0
3. 确认能看到README和全部20个ZIP附件。

## 六、下载验证

在新目录克隆仓库，安装Python 3.10–3.12后执行：

```bash
git clone https://github.com/shaoyun233/SHBC-Gesture11.git
cd SHBC-Gesture11
python dataset/scripts/download_dataset.py --repo shaoyun233/SHBC-Gesture11 --tag v1.0.0 --extract
python dataset/scripts/verify_dataset.py --check-frames
```

下载约36.75 GB，解压后的图像另占约36.72 GB，请预留空间。验证成功应得到20个分卷、202781帧。程序运行见根README；该包包含数据发布和两个演示应用，不包含工作区内全部训练实验代码。

## 可选：命令行上传数据附件

如果浏览器上传不稳定，安装GitHub CLI，先运行 `gh auth login`。创建Release草稿后，在PowerShell执行：

```powershell
$archiveDir = 'D:\替换成你的解压位置\SHBC-Gesture11-Full-Release\release-assets'
Get-ChildItem -LiteralPath $archiveDir -Filter '*.zip' | Sort-Object Name | ForEach-Object {
    gh release upload v1.0.0 $_.FullName --repo shaoyun233/SHBC-Gesture11
    if ($LASTEXITCODE -ne 0) { throw "Upload failed: $($_.Name)" }
}
gh release upload v1.0.0 "$archiveDir\manifest.json" "$archiveDir\SHA256SUMS.txt" --repo shaoyun233/SHBC-Gesture11
```

若附件已存在，不要整批重复上传；仅补传缺失附件。需要替换某个附件时，先核对对象再单独使用 `--clobber`。

本包数据分卷已完成SHA-256、字节数和帧数核对；应用源码已做语法检查，尚无摄像头和GPU实机运行验证。图3、图7见figures，图7按旧版流程图编号，论文引用需对应调整。

官方依据：[网页上传文件](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)、[发布Release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)、[Release附件限制](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)、[MIT](https://opensource.org/license/mit)、[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。
