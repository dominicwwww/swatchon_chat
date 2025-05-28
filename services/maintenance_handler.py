from services.settlement_service import SettlementService

class MaintenanceHandler:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.settlement_service = None

    def process_maintenance_fee(self, data):
        try:
            print("관리비 정산 처리 시작...")
            if self.settlement_service is None:
                print("SettlementService 초기화 중...")
                self.settlement_service = SettlementService(self.config_manager)
            
            # data는 한 건만 리스트로 들어옴
            print(f"정산 데이터 처리: {data[0]}")
            result = self.settlement_service.create_settlement(data[0])
            
            # 작업 완료 후 드라이버 정리는 하지 않음 (재사용을 위해)
            # if self.settlement_service:
            #     print("SettlementService 정리 중...")
            #     self.settlement_service.quit()
            #     self.settlement_service = None
            
            print(f"관리비 정산 처리 완료: {result}")
            return result
        except Exception as e:
            print(f"정산서 자동화 오류: {e}")
            import traceback
            traceback.print_exc()
            # 오류 발생 시에도 드라이버 정리
            if self.settlement_service:
                print("오류 발생으로 인한 SettlementService 정리...")
                self.settlement_service.quit()
                self.settlement_service = None
            return False
    
    def cleanup(self):
        """모든 작업 완료 후 정리"""
        if self.settlement_service:
            print("SettlementService 정리 중...")
            self.settlement_service.quit()
            self.settlement_service = None 