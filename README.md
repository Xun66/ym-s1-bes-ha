# YM-S1-BES BLE 电量计 Home Assistant 本地集成

这是给芝码/云目 `YM-S1-BES` BLE 电量计插座使用的 Home Assistant 自定义集成。

它不依赖原厂小程序和云端，直接通过 Home Assistant 的 Bluetooth 集成或 ESPHome Bluetooth Proxy 主动连接设备，读取实时功率、电压、电流、累计电量等数据，并提供四个清零按钮。

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

## 注意

清零按钮会直接修改设备累计数据。建议先确认设备已经正常读取，再使用清零功能。
