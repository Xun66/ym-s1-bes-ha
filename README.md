# YM-S1-BES BLE 电量计 Home Assistant 本地集成

这是给芝码/云目 `YM-S1-BES` BLE 电量计插座使用的 Home Assistant 自定义集成。

它不依赖原厂小程序和云端，直接通过 Home Assistant 的 Bluetooth 集成或 ESPHome Bluetooth Proxy 主动连接设备，读取实时功率、电压、电流、累计电量等数据，并提供四个清零按钮、电价/计时功率设置和虚拟负载设备。

## 已验证设备

- 型号：`YM-S1-BES`
- 固件：`V1`
- 通信方式：BLE GATT
- 已实机验证：
  - 读取功率/电压/电流/累计电量
  - 电量清零
  - 时间清零
  - 金额清零
  - 全部清零
  - 设置电价
  - 设置计时功率

## 实体

传感器：

- 功率
- 累计电量
- 电压
- 电流
- 功率因数
- 累计时间
- 累计金额
- 有效功率

按钮：

- 清零电量
- 清零时间
- 清零金额
- 全部清零

数字：

- 电价，单位 `CNY/kWh`
- 计时功率，单位 `W`

负载：

- 在集成选项中可以新增、切换、重命名、删除“负载”。
- 每个负载会在 Home Assistant 中生成一个独立 Device。
- 负载只继承瞬态数据：功率、电压、电流、功率因数。
- 只有当前选中的负载显示实时值，其他负载实体保持不可用。

## 安装

### 方式一：手动安装

把仓库里的目录复制到 Home Assistant：

```text
custom_components/ym_s1_bes -> /config/custom_components/ym_s1_bes
```

然后重启 Home Assistant。

### 方式二：HACS 自定义仓库

在 HACS 中添加自定义仓库：

```text
https://github.com/Xun66/ym-s1-bes-ha
```

类型选择：

```text
Integration
```

安装后重启 Home Assistant。

## ESPHome Bluetooth Proxy 要求

如果通过 ESPHome Bluetooth Proxy 接入，需要启用 active connections：

```yaml
bluetooth_proxy:
  active: true
```

## 添加设备

在 Home Assistant 中：

```text
设置 -> 设备与服务 -> 添加集成 -> YM-S1-BES BLE Meter
```

手动添加时填写设备 MAC。BLE address 通常可以留空，只要 Home Assistant 已经通过蓝牙或 Bluetooth Proxy 看到设备广播。

本集成会根据设备 MAC 自动计算广播名：

```text
MAC: 25:01:10:00:0B:D6
广播名: YUNMD60B00100125
```

## 协议说明

设备使用私有 BLE 协议：

- Service UUID: `49535343-fe7d-4ae5-8fa9-9fafd205e455`
- Notify UUID: `49535343-1e4d-4bd9-ba61-23c647249616`
- Write UUID: `49535343-8841-43f4-a8d4-ecbe34729bb3`
- 写入方式：`write-without-response`

实机验证后，该设备使用 `EC ED` mode1 长帧：

```text
EC ED LEN_H LEN_L PAYLOAD CRC_H CRC_L
```

整帧再按 MAC 派生出的 `xorKey` 逐字节 XOR。

业务 payload 还会按命令层 XOR `0xE9`。已知命令：

```text
读取:      08 00 08
清零电量:  07 02 01 FE 08
清零时间:  07 02 02 FD 08
清零金额:  07 02 03 FC 08
全部清零:  07 02 00 FF 08
设置配置:  2D 04 PWR_H PWR_L PRICE_H PRICE_L SUM
```

`SUM` 是前 6 个逻辑字节求和后取低 8 位。发送前，逻辑 payload 每字节 XOR `0xE9`。

例如电价 `0.20 CNY/kWh`、计时功率 `10 W` 的逻辑 payload 是：

```text
2D 04 00 0A 00 14 4F
```

实际业务 payload 是：

```text
C4 ED E9 E3 E9 FD A6
```

## 注意

清零按钮会直接修改设备累计数据。建议先确认设备已经正常读取，再使用清零功能。
