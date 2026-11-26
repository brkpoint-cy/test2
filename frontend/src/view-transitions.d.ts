interface Document {
  startViewTransition?: (options: {
    update: () => void
    types?: string[]
  }) => {
    finished: Promise<void>
  }
}
