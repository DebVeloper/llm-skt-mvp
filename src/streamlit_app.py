"""
Streamlit application for SQL Query Agent - Refactored with object-oriented design.
"""

import streamlit as st
import uuid
import logging
from typing import Optional, Dict, Any, List
from langgraph.pregel import Command

from SQL_Query_Agent import SQLQueryAgent
from config import ConfigManager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionStateManager:
    """세션 상태 관리 클래스"""
    
    def __init__(self):
        """세션 상태 초기화"""
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """세션 상태 초기화"""
        # 메시지 히스토리
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        
        # SQL Query Agent 인스턴스
        if 'agent' not in st.session_state:
            st.session_state.agent = None
        
        # 워크플로우 상태
        if 'thread_id' not in st.session_state:
            st.session_state.thread_id = str(uuid.uuid4())
        
        if 'current_interrupt' not in st.session_state:
            st.session_state.current_interrupt = None
        
        if 'workflow_state' not in st.session_state:
            st.session_state.workflow_state = 'waiting_for_question'
        
        # UI 상태
        if 'buttons_disabled' not in st.session_state:
            st.session_state.buttons_disabled = False
        
        if 'query_suggestions_displayed' not in st.session_state:
            st.session_state.query_suggestions_displayed = False
        
        if 'interaction_panel_cleared' not in st.session_state:
            st.session_state.interaction_panel_cleared = False
        
        if 'feedback_sent' not in st.session_state:
            st.session_state.feedback_sent = False
        
        if 'pending_feedback' not in st.session_state:
            st.session_state.pending_feedback = None
    
    def add_message(self, role: str, content: str):
        """메시지 추가"""
        st.session_state.messages.append({"role": role, "content": content})
    
    def reset_session(self):
        """세션 초기화"""
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.current_interrupt = None
        st.session_state.workflow_state = 'waiting_for_question'
        st.session_state.buttons_disabled = False
        st.session_state.query_suggestions_displayed = False
        st.session_state.interaction_panel_cleared = False
        st.session_state.feedback_sent = False
        st.session_state.pending_feedback = None
    
    def set_workflow_state(self, state: str):
        """워크플로우 상태 설정"""
        st.session_state.workflow_state = state
    
    def set_processing_state(self):
        """처리 상태로 설정"""
        st.session_state.workflow_state = 'processing'
        st.session_state.interaction_panel_cleared = False
    
    def set_feedback_waiting_state(self):
        """피드백 대기 상태로 설정"""
        st.session_state.workflow_state = 'waiting_for_feedback'
        st.session_state.buttons_disabled = False
        st.session_state.query_suggestions_displayed = False
        st.session_state.feedback_sent = False
    
    def set_completion_state(self):
        """완료 상태로 설정"""
        st.session_state.workflow_state = 'waiting_for_question'
        st.session_state.buttons_disabled = False
        st.session_state.query_suggestions_displayed = False
        st.session_state.interaction_panel_cleared = True
        st.session_state.feedback_sent = False
        st.session_state.pending_feedback = None


class UIManager:
    """UI 관리 클래스"""
    
    def __init__(self, session_manager: SessionStateManager):
        """UI 매니저 초기화"""
        self.session_manager = session_manager
    
    def setup_page(self):
        """페이지 설정"""
        st.set_page_config(
            page_title="SQL Query Agent",
            page_icon="🗃️",
            layout="wide"
        )
        
        st.title("🗃️ SQL Query Agent")
        st.markdown("자연어 질문을 SQL 쿼리로 변환하고 실행하는 AI 어시스턴트")
    
    def display_messages(self):
        """메시지 히스토리 표시"""
        for i, message in enumerate(st.session_state.messages):
            is_last_message = (i == len(st.session_state.messages) - 1)
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if is_last_message:
                    st.markdown("---")
                    st.markdown(
                        '<div id="latest-message" style="height: 1px;"></div>',
                        unsafe_allow_html=True
                    )
        
        # 자동 스크롤 스크립트
        if st.session_state.messages:
            st.markdown("""
            <script>
            setTimeout(function() {
                var latestMessage = document.getElementById('latest-message');
                if (latestMessage) {
                    latestMessage.scrollIntoView({ behavior: 'smooth', block: 'end' });
                }
            }, 200);
            </script>
            """, unsafe_allow_html=True)
    
    def display_query_suggestions(self, interrupt_data: Dict[str, Any]) -> Optional[str]:
        """쿼리 제안 표시"""
        st.write("**🔍 생성된 SQL 쿼리 제안**")
        
        # 쿼리 제안 데이터 추출
        query_suggestions = self._extract_query_suggestions(interrupt_data)
        
        if not query_suggestions:
            st.warning("생성된 쿼리를 찾을 수 없습니다.")
            return None
        
        # 쿼리 제안을 메시지로 추가 (처음에만)
        if not st.session_state.query_suggestions_displayed:
            self._add_suggestions_to_messages(query_suggestions)
            st.session_state.query_suggestions_displayed = True
            st.rerun()
        
        # UI에 제안 표시
        self._display_suggestion_ui(query_suggestions)
        
        # 사용자 선택 옵션 표시
        return self._display_selection_options()
    
    def _extract_query_suggestions(self, interrupt_data: Dict[str, Any]) -> List[tuple]:
        """쿼리 제안 데이터 추출"""
        query_suggestions = []
        
        if isinstance(interrupt_data, dict):
            if 'query_suggestions' in interrupt_data:
                query_suggestions = interrupt_data['query_suggestions']
            elif 'query_suggestion' in interrupt_data:
                query_suggestions = interrupt_data['query_suggestion']
        
        # 현재 상태에서 쿼리 제안 가져오기
        if not query_suggestions and st.session_state.agent:
            current_state = st.session_state.agent.get_state({
                "configurable": {"thread_id": st.session_state.thread_id}
            })
            if current_state and current_state.values:
                if 'query_suggestion' in current_state.values:
                    query_suggestions = current_state.values['query_suggestion']
        
        return self._process_query_suggestions(query_suggestions)
    
    def _process_query_suggestions(self, query_suggestions: List[tuple]) -> List[tuple]:
        """쿼리 제안 처리 및 정리"""
        if not query_suggestions:
            return []
        
        # 최근 3개 제안만 사용
        if len(query_suggestions) > 3:
            recent_suggestions = query_suggestions[-3:]
        else:
            recent_suggestions = query_suggestions
        
        # agent 이름별로 최신 제안만 유지
        latest_suggestions = {}
        for agent_name, query_data in recent_suggestions:
            latest_suggestions[agent_name] = query_data
        
        # agent 순서대로 정렬
        agent_order = ["query_agent_1", "query_agent_2", "query_agent_3"]
        display_suggestions = []
        for agent_name in agent_order:
            if agent_name in latest_suggestions:
                display_suggestions.append((agent_name, latest_suggestions[agent_name]))
        
        return display_suggestions
    
    def _add_suggestions_to_messages(self, suggestions: List[tuple]):
        """제안을 메시지로 추가"""
        suggestion_message = "🔍 **생성된 SQL 쿼리 제안**\n\n"
        
        for i, (agent_name, query_data) in enumerate(suggestions, 1):
            suggestion_message += f"**옵션 {i} - {agent_name}**\n"
            suggestion_message += f"```sql\n{query_data.get('query', '')}\n```\n"
            
            if 'suggestion' in query_data and query_data['suggestion']:
                suggestion_message += "**개선 제안:**\n"
                for suggestion in query_data['suggestion']:
                    suggestion_message += f"• {suggestion}\n"
            suggestion_message += "\n"
        
        self.session_manager.add_message("assistant", suggestion_message)
    
    def _display_suggestion_ui(self, suggestions: List[tuple]):
        """제안 UI 표시"""
        for i, (agent_name, query_data) in enumerate(suggestions, 1):
            with st.expander(f"옵션 {i} - {agent_name}", expanded=True):
                st.code(query_data.get('query', ''), language='sql')
                
                if 'suggestion' in query_data and query_data['suggestion']:
                    st.write("**개선 제안:**")
                    for suggestion in query_data['suggestion']:
                        st.write(f"• {suggestion}")
    
    def _display_selection_options(self) -> Optional[str]:
        """선택 옵션 표시"""
        st.write("**선택 옵션:**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("옵션 1 실행", key="opt1", disabled=st.session_state.buttons_disabled):
                st.session_state.buttons_disabled = True
                return "1"
        
        with col2:
            if st.button("옵션 2 실행", key="opt2", disabled=st.session_state.buttons_disabled):
                st.session_state.buttons_disabled = True
                return "2"
        
        with col3:
            if st.button("옵션 3 실행", key="opt3", disabled=st.session_state.buttons_disabled):
                st.session_state.buttons_disabled = True
                return "3"
        
        with col4:
            if st.button("실행 취소", key="cancel", disabled=st.session_state.buttons_disabled):
                st.session_state.buttons_disabled = True
                return "cancel"
        
        return None
    
    def display_question_input(self, key_suffix: str = "") -> Optional[str]:
        """질문 입력 UI 표시"""
        st.write("**💬 새로운 질문**")
        question = st.text_input(
            "데이터베이스에 대한 질문을 입력하세요:",
            key=f"question_input{key_suffix}"
        )
        
        if st.button("질문 전송") and question:
            return question
        
        return None
    
    def display_feedback_input(self) -> Optional[str]:
        """피드백 입력 UI 표시"""
        st.write("**💬 추가 피드백**")
        feedback = st.text_input(
            "쿼리 수정이 필요하면 피드백을 입력하세요:",
            key="feedback_input"
        )
        
        if st.button("피드백 전송", disabled=st.session_state.buttons_disabled) and feedback:
            return feedback
        
        return None
    
    def display_sidebar(self):
        """사이드바 표시"""
        with st.sidebar:
            st.header("🔧 세션 제어")
            
            if st.button("새 대화 시작"):
                self.session_manager.reset_session()
                st.rerun()
            
            st.subheader("ℹ️ 정보")
            st.write(f"**Thread ID:** {st.session_state.thread_id[:8]}...")
            st.write(f"**상태:** {st.session_state.workflow_state}")
            
            st.subheader("📖 사용 방법")
            st.markdown("""
            1. **질문 입력**: 데이터베이스에 대한 자연어 질문을 입력
            2. **쿼리 선택**: 생성된 3개의 SQL 쿼리 중 하나를 선택
            3. **결과 확인**: 쿼리 실행 결과 및 개선 제안 확인
            4. **피드백**: 필요시 추가 피드백으로 쿼리 수정
            """)


class WorkflowController:
    """워크플로우 제어 클래스"""
    
    def __init__(self, session_manager: SessionStateManager, ui_manager: UIManager):
        """워크플로우 컨트롤러 초기화"""
        self.session_manager = session_manager
        self.ui_manager = ui_manager
    
    def initialize_agent(self):
        """SQL Query Agent 초기화"""
        if st.session_state.agent is None:
            with st.spinner("SQL Query Agent 초기화 중..."):
                try:
                    config = ConfigManager()
                    st.session_state.agent = SQLQueryAgent(config).get_graph()
                    logger.info("SQL Query Agent initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize SQL Query Agent: {e}")
                    st.error(f"Agent 초기화 실패: {str(e)}")
                    raise
    
    def process_initial_question(self, question: str) -> bool:
        """초기 질문 처리"""
        try:
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            initial_state = {
                "user_request": question,
                "user_feedback": "",
                "selected_query": None,
                "query_suggestion": [],
                "refactoring_suggestion": None,
                "query_result": None,
                "error_message": None,
                "messages": []
            }
            
            # 워크플로우 스트림 실행
            events = list(st.session_state.agent.stream(initial_state, config))
            
            # 메시지 처리
            self._process_workflow_events(events)
            
            # 현재 상태 확인
            state = st.session_state.agent.get_state(config)
            return self._handle_workflow_state(state)
            
        except Exception as e:
            logger.error(f"Initial question processing failed: {e}")
            st.error(f"오류가 발생했습니다: {str(e)}")
            self.session_manager.set_completion_state()
            return False
    
    def process_feedback(self, feedback: str) -> bool:
        """피드백 처리"""
        try:
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            
            # 피드백으로 워크플로우 재개
            events = list(st.session_state.agent.stream(
                Command(resume=feedback), config
            ))
            
            # 메시지 처리
            self._process_workflow_events(events)
            
            # 현재 상태 확인
            state = st.session_state.agent.get_state(config)
            return self._handle_workflow_state(state)
            
        except Exception as e:
            logger.error(f"Feedback processing failed: {e}")
            st.error(f"오류가 발생했습니다: {str(e)}")
            self.session_manager.set_completion_state()
            return False
    
    def _process_workflow_events(self, events: List[Dict[str, Any]]):
        """워크플로우 이벤트 처리"""
        for event in events:
            if isinstance(event, dict):
                for node_name, node_data in event.items():
                    if isinstance(node_data, dict) and 'messages' in node_data:
                        for msg in node_data['messages']:
                            if hasattr(msg, 'content'):
                                self.session_manager.add_message("assistant", msg.content)
    
    def _handle_workflow_state(self, state: Any) -> bool:
        """워크플로우 상태 처리"""
        if state.next:
            # 인터럽트 발생
            interrupt_data = self._extract_interrupt_data(state)
            st.session_state.current_interrupt = interrupt_data
            self.session_manager.set_feedback_waiting_state()
            return True
        else:
            # 워크플로우 완료
            st.session_state.current_interrupt = None
            self.session_manager.set_completion_state()
            return False
    
    def _extract_interrupt_data(self, state: Any) -> Dict[str, Any]:
        """인터럽트 데이터 추출"""
        interrupt_data = None
        
        if hasattr(state, 'tasks') and state.tasks:
            for task in state.tasks:
                if hasattr(task, 'interrupts') and task.interrupts:
                    interrupt_data = task.interrupts[0]
                    break
        
        return interrupt_data or state.values


class StreamlitApp:
    """메인 Streamlit 애플리케이션 클래스"""
    
    def __init__(self):
        """애플리케이션 초기화"""
        self.session_manager = SessionStateManager()
        self.ui_manager = UIManager(self.session_manager)
        self.workflow_controller = WorkflowController(self.session_manager, self.ui_manager)
    
    def run(self):
        """애플리케이션 실행"""
        # 페이지 설정
        self.ui_manager.setup_page()
        
        # Agent 초기화
        self.workflow_controller.initialize_agent()
        
        # 펜딩 피드백 처리
        self._handle_pending_feedback()
        
        # 메인 레이아웃
        self._render_main_layout()
        
        # 사이드바
        self.ui_manager.display_sidebar()
    
    def _handle_pending_feedback(self):
        """펜딩 피드백 처리"""
        if st.session_state.pending_feedback:
            feedback = st.session_state.pending_feedback
            st.session_state.pending_feedback = None
            
            has_interrupt = self.workflow_controller.process_feedback(feedback)
            st.rerun()
    
    def _render_main_layout(self):
        """메인 레이아웃 렌더링"""
        col1, col2 = st.columns([1.2, 0.8])
        
        # 왼쪽: 대화 히스토리
        with col1:
            st.subheader("💬 대화 이력")
            with st.container(height=600, border=True):
                self.ui_manager.display_messages()
        
        # 오른쪽: 현재 상호작용
        with col2:
            st.subheader("🔄 현재 상호작용")
            with st.container(height=600, border=True):
                self._render_interaction_panel()
    
    def _render_interaction_panel(self):
        """상호작용 패널 렌더링"""
        workflow_state = st.session_state.workflow_state
        
        if workflow_state == 'waiting_for_question' or st.session_state.interaction_panel_cleared:
            self._render_question_input()
        elif workflow_state == 'waiting_for_feedback':
            self._render_feedback_input()
        elif workflow_state == 'processing':
            self._render_processing_state()
    
    def _render_question_input(self):
        """질문 입력 렌더링"""
        if st.session_state.interaction_panel_cleared:
            st.success("✅ 피드백 처리가 완료되었습니다!")
            st.info("새로운 질문을 입력하여 다시 시작하세요.")
            key_suffix = "_new"
        else:
            key_suffix = ""
        
        question = self.ui_manager.display_question_input(key_suffix)
        
        if question:
            self.session_manager.add_message("user", question)
            self.session_manager.set_processing_state()
            
            with st.spinner("쿼리 생성 중..."):
                has_interrupt = self.workflow_controller.process_initial_question(question)
            
            st.rerun()
    
    def _render_feedback_input(self):
        """피드백 입력 렌더링"""
        if st.session_state.current_interrupt:
            # 쿼리 제안 표시
            selected_option = self.ui_manager.display_query_suggestions(
                st.session_state.current_interrupt
            )
            
            if selected_option:
                self.session_manager.add_message("user", f"선택: {selected_option}")
                self.session_manager.set_processing_state()
                st.session_state.feedback_sent = True
                st.session_state.pending_feedback = selected_option
                st.rerun()
            
            # 추가 피드백 입력
            feedback = self.ui_manager.display_feedback_input()
            
            if feedback:
                self.session_manager.add_message("user", feedback)
                self.session_manager.set_processing_state()
                st.session_state.buttons_disabled = True
                st.session_state.feedback_sent = True
                st.session_state.pending_feedback = feedback
                st.rerun()
    
    def _render_processing_state(self):
        """처리 상태 렌더링"""
        if not st.session_state.feedback_sent:
            st.info("처리 중...")


def main():
    """메인 함수"""
    try:
        app = StreamlitApp()
        app.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"애플리케이션 오류: {str(e)}")


if __name__ == "__main__":
    main() 