"""
데이터 매니저
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from pathlib import Path

class DataManager:
    """데이터 관리 클래스"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
    
    def load_maintenance_fee_data(self, year: int, month: int) -> List[Dict[str, Any]]:
        """관리비 데이터 로드 (임시 데이터)"""
        return [
            {
                'date': f'{year}-{month:02d}-01',
                'unit_number': '101',
                'supply_amount': 100000,
                'vat_amount': 10000
            },
            {
                'date': f'{year}-{month:02d}-01',
                'unit_number': '102',
                'supply_amount': 150000,
                'vat_amount': 15000
            }
        ]
    
    def export_maintenance_fee_to_excel(self, year: int, month: int, unit_number: Optional[str] = None):
        """관리비 데이터를 엑셀로 내보내기 (임시 구현)"""
        data = self.load_maintenance_fee_data(year, month)
        if unit_number:
            data = [item for item in data if item.get('unit_number') == unit_number]
        df = pd.DataFrame(data)
        columns = ['date', 'unit_number', 'supply_amount', 'vat_amount']
        df = df[columns]
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        filename = f"maintenance_fee_{year}_{month:02d}"
        if unit_number:
            filename += f"_{unit_number}"
        filename += ".xlsx"
        output_path = output_dir / filename
        df.to_excel(output_path, index=False)
        return output_path 