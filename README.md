# The Shooting Star 全版本简体中文汉化

**本仓库仅提供简体中文汉化与整理发布，维护者并非原模组作者。原模组由 rimuru.dev 开发，程序、玩法与素材等原作内容的权利归原作者所有。**

> 全部汉化由 Codex 制作。若汉化有语法问题，请找 OpenAI。

覆盖截至 **2026-11-01** 原作者发布列表公开列出的全部 **65 个文件**，对应 **28 个发布名称（含热修复）**，从 **1.0.2A 到 1.5.0**。

**[全部版本下载表](VERSIONS.md)** · **[完整发布页](https://github.com/VyskoyeNebo/the-shooting-star-zh-cn/releases/tag/all-versions-2026-11-01)** · **[SHA-256 校验](SHA256SUMS-ALL.txt)**

## 1.5.0 快速下载

| 加载器 | 游戏版本（包内声明） | 下载 |
| --- | --- | --- |
| Fabric（26.3 Hotfix） | 1.20.1、1.21.1、1.21.11、26.3 | [汉化 JAR](https://github.com/VyskoyeNebo/the-shooting-star-zh-cn/releases/download/all-versions-2026-11-01/the-shooting-star-demo-1.5.0-fabric--cf9378124--zh_cn.jar) |
| Forge | 1.20.1、1.21.1 | [汉化 JAR](https://github.com/VyskoyeNebo/the-shooting-star-zh-cn/releases/download/all-versions-2026-11-01/the-shooting-star-demo-1.5.0-forge--cf9377538--zh_cn.jar) |
| NeoForge | 1.20.1、1.21.1 | [汉化 JAR](https://github.com/VyskoyeNebo/the-shooting-star-zh-cn/releases/download/all-versions-2026-11-01/the-shooting-star-demo-1.5.0-neoforge--cf9377531--zh_cn.jar) |

1.5.0 需要相同加载器的 **RimuLib 1.1.5+**；Forge/NeoForge 包声明的范围为 `[1.1.5,2.0)`。Fabric 分支还需对应游戏版本的 Fabric API。请以包内依赖声明为准。

## 安装

1. 在下载表中同时匹配模组版本、加载器和 Minecraft 版本。
2. 退出游戏，将该模组的原 JAR 移出所选实例的 `mods` 文件夹留作备份。
3. 放入对应的汉化 JAR，保留原包要求的前置。不要同时加载原版和汉化版主模组，也不要同时安装本模组的多个历史版本。
4. 游戏语言选择“简体中文”，启动所选实例。

需要 RimuLib 的版本已附带共用菜单中文资源；仍需安装 RimuLib 原版前置本体。[RimuLib 原作者发布页](https://www.curseforge.com/minecraft/mc-mods/rimulib)。

早期通用包对不同加载器支持的 Minecraft 版本不同，例如 1.0.7 Nvidia 的 Forge/旧 NeoForge 部分适用于 1.20.1；不要用于 NeoForge 1.21.11。完整组合见下载表。

## 汉化内容与保留部分

- 逐版本翻译物品、方块、技能说明、字幕、菜单、提示和参数滑块。
- 翻译代码内的 HUD、状态提示与星名，包括混淆代码中保存的固定文本。
- 依照各版原文保留数值差异，例如早期 360 格与后期 1,440 格的七星范围，以及不同的轨道炮滑块上限。
- 需要 RimuLib 的版本附带其共用界面中文。
- 原作五个以线条字形绘制的英文技能动画标题保留英文，技能菜单中的名称与说明已翻译。

英文语言文件保留。每个包的模组 ID、依赖、数值常量、方法指令、技能解锁条件、着色器、模型、音频及材质保持原样；仅修改中文资源、文本常量及其文本链接，并翻译模组列表名称。

## 验证情况

全部 **65/65** 文件已完成压缩包完整性、JSON/TOML、语言键覆盖和格式占位符检查。包括内置包，共检查 **161** 个 JAR 归档，反汇编检查 **3094** 个修改的类，并在 Java 虚拟机上验证 **3348** 个中文文本调用点。

**尚未逐版本进入 Minecraft 实测。** 具体原始文件、原始及汉化 SHA-256、包内加载声明、检查统计见 [versions.json](versions.json)。

## 仓库内容

- `VERSIONS.md`：全部 65 个文件的下载、兼容组合与原始发布页。
- `versions.json`：逐包来源、校验和、依赖与验证统计。
- `translations/archive/<CurseForge 文件 ID>/`：逐包、逐内置游戏版本的中文语言资源。
- `translations/rimulib/zh_cn.json`：共用菜单中文资源。
- `SHA256SUMS-ALL.txt`：本次全部汉化附件的 SHA-256。

完整汉化 JAR 位于 Releases；单独的语言 JSON 不包含代码内 HUD 文本修改。

## 原作者与权利说明

本项目为非官方汉化，翻译由 **Codex** 制作，**VyskoyeNebo 仅整理发布汉化**。原模组作者为 **rimuru.dev**。

- [原作者 CurseForge 项目](https://www.curseforge.com/minecraft/mc-mods/the-shooting-star-demo)
- [原始完整文件列表](https://www.curseforge.com/minecraft/mc-mods/the-shooting-star-demo/files/all)
- [原作者页面](https://www.tiktok.com/@rimuru.dev)

原模组声明为 **All Rights Reserved**。原模组程序及素材的权利归原作者，本项目保留其作者信息与权利声明。
