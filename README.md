# PlantMeta

PlantMeta 是桌面植物智能养护盒项目的软件端。当前第一步先实现一个最小 FastAPI 后端，用于接收模拟 ESP32 传感器数据、进行简单植物状态判断，并提供基础查询接口。

## 项目启动

### 启动后端

```powershell
cd "D:\vscode-project\python\Courses\2026_spring\Introduction-to-Engineering\PlantMeta"
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload
```

打开 API 文档：

```text
http://127.0.0.1:8000/docs
```


### 模拟上传数据

fake ESP32 当前模拟并上传以下核心数据：

- `soil_moisture_raw`：土壤湿度传感器原始值。
- `soil_moisture_percent`：土壤湿度百分比。
- `light_lux`：BH1750 光照强度，单位 lux。
- `air_temperature`：DHT22 温度，单位摄氏度。
- `air_humidity`：DHT22 空气湿度百分比。
- `pump_status`：当前水泵状态，暂时为 `off`。
- `device_id`：设备编号。
- `plant_id`：植物编号。

示例请求体：

```json
{
  "device_id": "plant_box_01",
  "plant_id": "pothos_01",
  "pump_status": "off",
  "soil_moisture_raw": 2380,
  "soil_moisture_percent": 42.5,
  "light_lux": 680,
  "air_temperature": 24.8,
  "air_humidity": 56.2
}
```

后端会返回控制响应，例如：

```json
{
  "status": "normal",
  "command": "none",
  "pump_duration_ms": 0,
  "led_status": "green",
  "message": "Plant status is normal."
}
```


### 运行 fake ESP32

`backend/scripts/fake_esp32.py` 用于在真实硬件完成前模拟 ESP32。它会生成传感器数据，并周期性向后端发送：

```text
POST http://127.0.0.1:8000/api/sensor/upload
```

先保持后端运行，再打开另一个 PowerShell 终端：

```powershell
cd "D:\vscode-project\python\Courses\2026_spring\Introduction-to-Engineering\PlantMeta"
.\.venv\Scripts\Activate.ps1
python backend\scripts\fake_esp32.py normal
```

可选模拟场景：

- `normal`：正常环境数据。
- `dry`：土壤湿度逐渐下降，并带有轻微波动，便于观察曲线变化。
- `wet`：土壤湿度偏高。
- `strong_light`：光照过强。
- `cold`：温度偏低。
- `fault`：传感器异常数据。

示例：只发送 5 次缺水场景数据。

```powershell
python backend\scripts\fake_esp32.py dry --count 5 --interval 2
```

### 启动前端

前端用于测试后端、数据库、规则判断、浇水事件和 LLM 建议链路。

```powershell
cd "D:\vscode-project\python\Courses\2026_spring\Introduction-to-Engineering\PlantMeta\frontend"
npm install
npm run dev
```

默认访问：

```text
http://localhost:5173
```

推荐测试顺序：

1. 启动 FastAPI 后端。
2. 运行 fake ESP32 上传几条数据。
3. 打开前端页面查看实时数据和历史曲线。
4. 点击“生成建议”测试 LLM 或模板 fallback。
5. 点击“手动浇水测试”查看事件日志。

前端显示说明：

- 历史湿度曲线会根据最近数据动态缩放，模拟数据的轻微波动会更明显。
- 后端新生成的规则判断消息使用中文；旧数据中已经写入 MySQL 的英文消息不会自动改写。
- MySQL 中保存的时间按 UTC 处理，前端显示时会转换为北京时间。
- 浇水事件模式会在前端显示为中文，例如 `manual` 显示为“手动浇水”。


## 具体技术细节

### 当前技术栈

- 后端框架：FastAPI
- 后端运行服务：Uvicorn
- 当前数据存储：MySQL
- 前端：React + Vite


### 已有 API

- `GET /`：检查后端是否正在运行。
- `GET /health`：返回简单健康状态。
- `POST /api/sensor/upload`：接收 fake ESP32 或未来真实 ESP32 上传的传感器数据。
- `GET /api/latest`：返回最新一条传感器记录。
- `GET /api/history`：返回最近若干条传感器记录。
- `POST /api/water/manual`：记录一次手动浇水事件。
- `POST /api/water/auto`：开启或关闭自动浇水模式。
- `GET /api/events`：返回最近若干条浇水事件。
- `POST /api/advice`：基于最新传感器记录生成养护建议，并写入建议记录表。

### 数据库配置

项目使用 `.env` 保存本地数据库连接信息：

```env
DATABASE_URL=mysql+pymysql://plantmeta_user:<passport>@127.0.0.1:3306/plantmeta
LLM_API_KEY=<aikey>
LLM_BASE_URL=https://api.deepseek.com/chat/completions
LLM_MODEL=deepseek-v4-flash
LLM_TIMEOUT_SECONDS=20
```

真实 `.env` 中需要把 `<passport>` 替换成自己的 MySQL 密码，把 `<aikey>` 替换成自己的 LLM API Key。`.env.example` 只作为配置模板。


## 真实场景交接

当前 fake ESP32 是一个虚拟设备，用于在没有硬件时完成软件开发和接口验证。真实硬件完成后，硬件端只需要把 fake ESP32 替换成真实 ESP32，并按照同一套 HTTP JSON 协议请求 `/api/sensor/upload`，即可接入当前软件系统。

### 硬件端需要完成的任务

硬件端主要负责以下内容：

- ESP32 连接 WiFi，并能访问软件端电脑所在的局域网 IP。
- 读取土壤湿度传感器原始值，并换算为百分比。
- 读取 BH1750 光照强度，单位为 lux。
- 读取 DHT22 / SHT 系列温湿度数据。
- 按约定 JSON 格式向后端上传数据。
- 接收后端返回的控制响应，并根据 `led_status` 更新状态灯。
- 后续如果启用真实浇水控制，再根据 `command` 和 `pump_duration_ms` 控制水泵。

### 后端联调启动方式

硬件联调时，后端不能只监听 `127.0.0.1`，需要监听局域网地址：

```powershell
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

在软件端电脑上查看局域网 IP：

```powershell
ipconfig
```

找到当前 WiFi 网卡下的 IPv4 地址，例如：

```text
192.168.1.23
```

ESP32 上传地址应设置为：

```text
http://192.168.1.23:8000/api/sensor/upload
```

注意：`127.0.0.1` 对 ESP32 来说代表 ESP32 自己，不是软件端电脑。因此真实硬件不能请求 `http://127.0.0.1:8000`。

### ESP32 上传数据格式

ESP32 使用 `POST` 请求上传 JSON：

```text
POST /api/sensor/upload
Content-Type: application/json
```

请求体示例：

```json
{
  "device_id": "plant_box_01",
  "plant_id": "pothos_01",
  "pump_status": "off",
  "soil_moisture_raw": 2380,
  "soil_moisture_percent": 42.5,
  "light_lux": 680,
  "air_temperature": 24.8,
  "air_humidity": 56.2
}
```

字段说明：

- `device_id`：设备编号，第一台设备固定为 `plant_box_01` 即可。
- `plant_id`：植物编号，第一版固定为 `pothos_01` 即可。
- `pump_status`：当前水泵状态，取值为 `off` 或 `on`。
- `soil_moisture_raw`：土壤湿度传感器 ADC 原始值。
- `soil_moisture_percent`：校准后的土壤湿度百分比，范围建议为 `0-100`。
- `light_lux`：BH1750 读取的光照强度。
- `air_temperature`：环境温度，单位摄氏度。
- `air_humidity`：空气湿度百分比。

### 后端返回控制格式

ESP32 上传成功后，后端会返回 JSON：

```json
{
  "status": "normal",
  "command": "none",
  "pump_duration_ms": 0,
  "led_status": "green",
  "message": "当前绿萝状态正常，环境数据处于适宜范围。"
}
```

字段说明：

- `status`：植物状态，可能为 `normal`、`watch`、`danger`、`fault`。
- `command`：控制指令，可能为 `none`、`water`、`stop`。
- `pump_duration_ms`：建议水泵工作时长，单位毫秒。
- `led_status`：状态灯颜色，可能为 `green`、`yellow`、`red`、`blue`。
- `message`：给人看的状态说明，ESP32 可以忽略，前端会展示。

当前阶段为了安全，后端规则系统还不会自动下发真实浇水指令，通常返回 `command: "none"`。真实浇水闭环完成前，硬件端可以先只处理 LED 状态。

### 建议联调步骤

1. 软件端启动后端，并使用 `--host 0.0.0.0` 监听局域网。
2. 软件端启动前端，打开 `http://localhost:5173` 观察数据。
3. 硬件端先用固定 JSON 测试一次 HTTP POST。
4. 确认后端 `/docs`、前端页面、MySQL 表中都能看到上传数据。
5. 再接入真实传感器读数，逐项验证土壤湿度、光照、温度、空气湿度。
6. 最后再接 LED 和水泵控制，先测试 LED，后测试水泵。

### 硬件安全约定

- 水泵不能直接接 ESP32 GPIO，必须通过继电器或 MOS 管驱动模块。
- ESP32、驱动模块和水泵供电需要共地。
- 水泵单次工作时长必须设置上限，建议不超过 `3000 ms`。
- `status` 为 `fault` 时，硬件端必须禁止浇水。
- `command` 为 `stop` 时，硬件端应立即停止执行器动作。
- 真实自动浇水完成前，硬件端不要自行用“湿度低于阈值”直接开泵，应等待后端明确返回 `command: "water"`。

### 土壤湿度校准建议

硬件端需要记录两个参考值：

```text
raw_dry：传感器在空气中或干土中的读数
raw_wet：传感器在充分湿润土壤中的读数
```

如果传感器表现为“越干 raw 越大，越湿 raw 越小”，可用：

```text
soil_moisture_percent = (raw_dry - raw_current) / (raw_dry - raw_wet) * 100
```

最后需要把结果限制在 `0-100`：

```text
soil_moisture_percent = max(0, min(100, soil_moisture_percent))
```

### 软件端提供的支持

软件端已经提供：

- `/api/sensor/upload` 接收真实 ESP32 数据。
- `/api/latest` 给前端读取最新状态。
- `/api/history` 给前端绘制历史曲线。
- `/api/events` 查看浇水事件。
- `/api/advice` 生成 LLM 或模板养护建议。
- fake ESP32 脚本作为硬件端上传协议参考。
