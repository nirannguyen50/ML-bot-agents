# Parallel Backtesting System Architecture

## Overview
Hệ thống backtest có thể chạy đồng thời nhiều chiến lược trên nhiều khung thời gian sử dụng multiprocessing và distributed computing.

## Core Components

### 1. ParallelBacktestEngine (Main Controller)
- Quản lý toàn bộ quy trình backtest song song
- Khởi tạo worker processes/threads
- Phân phối tasks đến các workers
- Tổng hợp và so sánh kết quả

### 2. StrategyRegistry
- Đăng ký và quản lý các chiến lược trading
- Mỗi strategy có thể chạy trên nhiều timeframe
- Hỗ trợ parameter optimization

### 3. TaskDistributor
- Phân phối tasks đến workers (multiprocessing/distributed)
- Load balancing và fault tolerance
- Support cả multiprocessing và distributed computing (Redis/Dask)

### 4. ResultsAggregator
- Tổng hợp kết quả từ các workers
- Tính toán comparative metrics
- Chuẩn bị data cho dashboard

## Data Flow
1. User config → Strategy Registry (tạo các backtest tasks)
2. Task Distributor → phân phối tasks đến workers
3. Workers → chạy backtest engine hiện có
4. Results → Aggregator → Dashboard

## Integration Points
- Backtest Engine hiện có: gọi như một function trong worker
- Dashboard: cung cấp comparative analysis view
- Data Pipeline: sử dụng data đã được DS chuẩn bị