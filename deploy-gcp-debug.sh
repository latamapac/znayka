#!/bin/bash
# DEBUG version with error checking

set -e

export PROJECT_ID="znayka-fresh-1771794343"
export REGION="us-central1"

echo "Checking project..."
gcloud config set project $PROJECT_ID

echo "Checking Cloud SQL..."
gcloud sql instances describe znayka-db --format='value(state)'

echo "Enabling APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

echo "Trying Cloud Build with detailed logging..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/znayka --timeout=30m 2>&1 | tee build.log || {
    echo ""
    echo "❌ BUILD FAILED"
    echo ""
    echo "Checking logs..."
    BUILD_ID=$(gcloud builds list --limit=1 --format='value(id)')
    echo "Build ID: $BUILD_ID"
    echo ""
    echo "View full logs:"
    echo "  gcloud builds log $BUILD_ID"
    echo ""
    echo "Or open in console:"
    echo "  https://console.cloud.google.com/cloud-build/builds/$BUILD_ID?project=$PROJECT_ID"
    exit 1
}
