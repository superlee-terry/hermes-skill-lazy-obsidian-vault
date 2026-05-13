---
categories:
- game-development
description: Fixes for NestJS TypeORM entity compilation issues in 《浮生剑录》 - entity
  create(), nullable types, BigInt, patch lint misreports.
name: fusheng-nestjs-compile-fixes
summary: Fixes for NestJS TypeORM entity compilation issues in 《浮生剑录》 - entity create(),
  nullable types, BigInt, patch lint misreports.
triggers: []
---

# 《浮生剑录》 NestJS 编译错误修复指南

## Pitfall: patch lint 报 TS1240/TS2564/TS1206
- **症状**: patch 内置 lint 报 `TS1240: Unable to resolve signature of parameter decorator` 等错误.
- **原因**: patch lint 用的简化 tsconfig 缺 `emitDecoratorMetadata`, `experimentalDecorators`.
- **修复**: tsc 实际不报错 → 忽略 patch lint 误报.

## Pitfall: entity `create()` 不接受 `id`
- **症状**: `PrimaryColumn` 字段不能通过 `create()` 传 id.
- **修复**: 用 `new Entity()` + 属性赋值.

## Pitfall: `slot: string | null` 传给 `string` 字段
- **症状**: `FindOptionsWhere` 报类型不兼容.
- **修复**: 用 `item.slot!` 非空断言.

## Pitfall: `BigInt()` 赋值给 `number` 字段
- **症状**: TS2322 `BigInt` not compatible with `number`.
- **修复**: 直接传 `now` (已经是 number).

## Pitfall: `Affix[]` 不兼容 `Record<string, unknown>[]`
- **症状**: 数组类型不匹配.
- **修复**: 改为 `any[]` 或匹配类型定义.