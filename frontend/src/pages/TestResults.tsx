import PageLayout from '../components/layout/PageLayout'

export default function TestResults() {
  return (
    <PageLayout title="Test Results">
      <div className="p-6">
        <div className="bg-muted border border-border rounded-lg p-12 text-center">
          <h2 className="text-xl font-bold mb-2">Coming Soon</h2>
          <p className="text-secondary text-sm">
            This page hasn't been designed yet — we'll build it once the testing workflow is defined.
          </p>
        </div>
      </div>
    </PageLayout>
  )
}