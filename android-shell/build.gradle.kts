plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val androidVersionCode = providers.environmentVariable("MORDECAI_ANDROID_VERSION_CODE").orNull?.toIntOrNull() ?: 1
val androidVersionName = providers.environmentVariable("MORDECAI_ANDROID_VERSION_NAME").orNull ?: "0.1.0"

android {
    namespace = "ai.mordecai.shell"
    compileSdk = 35

    defaultConfig {
        applicationId = "ai.mordecai.shell"
        minSdk = 29
        targetSdk = 35
        versionCode = androidVersionCode
        versionName = androidVersionName

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-service:2.8.7")
    implementation("androidx.browser:browser:1.8.0")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
}