# DeepSeek 余额小宠物 🐱💨

一个可以一直挂在桌面上的可爱小宠物：蓝发deepseek女仆娘，头顶的思考气泡会**实时显示你 DeepSeek 账户的余额**。

![预览](宠物预览.png)

## 特性

- 置顶显示，不挡操作，拖到哪就在哪
- 气泡定时刷新 DeepSeek 余额（默认 60 秒）
- 宠物本体、气泡、两个小圆点可分别拖到任意位置，松开自动记住
- 右键可隐藏气泡与圆点（只留宠物本体）
- 右键可调整整体大小（0.8x / 1.0x / 1.2x / 1.5x / 2.0x），整只宠物等比缩放并记住
- 位置、大小、Key 都保存在本地 `config.json`

## 怎么用

1. 双击 `启动宠物.bat` 启动，宠物出现在屏幕左上角。
2. 在宠物上**右键 → 设置 API Key**，粘贴你的 DeepSeek API Key（`sk-...`）。
3. 气泡就会每隔一段时间自动刷新余额。

也可以手动准备配置：

```bash
cp config.example.json config.json   # 然后填入你的 api_key
```

## 安全说明

> ⚠️ `config.json` 保存你的**真实 API Key**，已被 `.gitignore` 排除，**请勿提交**。
> 仓库里只提供不带 Key 的 `config.example.json` 模板。

## 文件说明

- `pet.py` — 宠物主程序
- `pet.png` — 宠物形象（来自高清图 `_ref_hi.png`）
- `config.example.json` — 配置模板
- `启动宠物.bat` — 双击启动
- `使用说明.md` — 更详细的说明
- `make_assets_hires.py` — 从高清图生成宠物素材（一般不需要运行）

## 获取 DeepSeek API Key

登录 [DeepSeek 开放平台](https://platform.deepseek.com/) → “API Keys” → 新建一个，复制 `sk-` 开头的那串即可。
