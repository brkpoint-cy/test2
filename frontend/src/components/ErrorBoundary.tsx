import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface State { failed: boolean }

export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('AeriScope render error', error, info.componentStack)
  }

  render() {
    if (this.state.failed) return <div className="state-card error" role="alert"><AlertCircle size={28} /><h2>研究结果暂时无法显示</h2><p>产物结构可能不完整，请重新加载或重新运行实验。</p><button className="button secondary" onClick={() => window.location.reload()}><RefreshCw size={16} />重新加载</button></div>
    return this.props.children
  }
}
