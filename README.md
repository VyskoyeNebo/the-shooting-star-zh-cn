# The Shooting Star 简体中文汉化

**本人仅负责简体中文汉化与汉化适配，并非原模组作者。原模组由 rimuru.dev 开发，程序、玩法与素材等原作内容的权利归原作者所有。**

为 **The Shooting Star 1.5.0 Forge** 提供简体中文翻译，包含主模组及 RimuLib 提供的共用菜单。

**[下载汉化 JAR](https://github.com/VyskoyeNebo/the-shooting-star-zh-cn/releases/download/v1.5.0-zh-cn.1/the-shooting-star-demo-1.5.0-forge-1.20.1-zh_cn.jar)** · **[查看发布页](https://github.com/VyskoyeNebo/the-shooting-star-zh-cn/releases)**

## 使用环境

| 项目 | 版本 |
| --- | --- |
| Minecraft | 1.20.1 |
| Forge | 47.4.28 |
| The Shooting Star | 1.5.0 Forge |
| 前置 RimuLib | 1.2.0 Forge |
| 游戏语言 | 简体中文（zh_cn） |

本发布针对上述 Forge 环境制作。

## 安装

1. 退出游戏，将原 `the-shooting-star-demo-1.5.0-forge.jar` 移出该实例的 `mods` 文件夹，留作备份。
2. 从发布页下载 `the-shooting-star-demo-1.5.0-forge-1.20.1-zh_cn.jar`，放入同一个 `mods` 文件夹。
3. 保留前置 `rimulib-1.2.0-forge.jar`，不要同时加载原版和汉化版主模组。
4. 游戏语言选择“简体中文”，再启动该 Forge 实例。

RimuLib 的中文语言资源已随主模组汉化包提供，前置本体保持原样，无需替换。

## 翻译内容

- 主模组 180 条语言文本：物品、方块、五种技能说明、字幕、菜单、滑块和提示。
- RimuLib 87 条共用界面语言文本。
- 183 种直接写入代码的 HUD、状态提示和星名文本。
- 原作五个以线条字形绘制的英文技能动画标题保留英文，技能菜单中的名称和说明已翻译。

英文语言文件保留。模组 ID、依赖、技能解锁条件、方法代码、着色器、模型、音频及材质保持不变。

## 验证情况

已通过压缩包完整性、JSON/TOML、语言键覆盖、格式占位符检查；已反汇编检查全部 44 个修改的类，并在 Java 虚拟机上验证 378 个中文文本调用点。

**尚未启动 Minecraft 实测。** 可通过 `SHA256SUMS.txt` 核对发布文件。

## 仓库内容

- `translations/shooting_star_demo/zh_cn.json`：主模组语言资源。
- `translations/rimulib/zh_cn.json`：共用界面语言资源。
- `INSTALL-zh_CN.txt`：离线安装说明。
- `SHA256SUMS.txt`：汉化 JAR 的 SHA-256。

完整汉化 JAR 位于 Releases；上述 JSON 仅包含语言资源，不包含代码内的 HUD 文本修改。

## 原作者与权利说明

这是非官方汉化项目。汉化整理：**VyskoyeNebo（仅负责汉化）**。原模组作者为 **rimuru.dev**，原作者页面：<https://www.tiktok.com/@rimuru.dev>。

原模组声明为 **All Rights Reserved**。原模组程序及素材的权利归原作者，本项目保留其作者信息与权利声明。
