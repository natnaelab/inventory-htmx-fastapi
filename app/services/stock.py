from typing import Dict, List
from sqlalchemy.orm import Session
from app.models.hardware import Hardware, ModelEnum, StatusEnum
from app.core.config import settings


class StockService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_stock_counts(self) -> Dict[str, int]:
        stock_counts = {}
        
        for model in ModelEnum:
            count = self.db.query(Hardware).filter(
                Hardware.model == model,
                Hardware.status == StatusEnum.IN_STOCK
            ).count()
            stock_counts[model.value] = count
        
        return stock_counts
    
    def get_thresholds(self) -> Dict[str, int]:
        return {
            'AllInOne': settings.threshold_all_in_one,
            'Notebook': settings.threshold_notebook,
            'DockingStation': settings.threshold_docking_station,
            'MFF': settings.threshold_micro_form_factor,
            'Monitor': settings.threshold_monitor,
            'Backpack': settings.threshold_backpack,
        }

    def get_model_names(self) -> Dict[str, str]:
        return {
            'AllInOne': 'All-in-One PC',
            'Notebook': 'Notebook',
            'DockingStation': 'Docking Station',
            'MFF': 'Micro Form Factor',
            'Monitor': 'Monitor',
            'Backpack': 'Backpack',
        }
    
    def get_threshold_alerts(self) -> List[Dict]:
        stock_counts = self.get_stock_counts()
        thresholds = self.get_thresholds()
        model_names = self.get_model_names()
        alerts = []

        for model, threshold in thresholds.items():
            current_count = stock_counts.get(model, 0)
            if current_count < threshold:
                alerts.append({
                    'model': model,
                    'model_name': model_names.get(model, model),
                    'current_count': current_count,
                    'threshold': threshold
                })
        
        return alerts

    def get_stock_summary(self) -> Dict:
        stock_counts = self.get_stock_counts()
        alerts = self.get_threshold_alerts()
        thresholds = self.get_thresholds()
        model_names = self.get_model_names()

        return {
            'stock_counts': stock_counts,
            'alerts': alerts,
            'thresholds': thresholds,
            'model_names': model_names,
            'total_in_stock': sum(stock_counts.values()),
            'alert_count': len(alerts)
        }
