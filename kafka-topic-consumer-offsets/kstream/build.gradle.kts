plugins {
    application
    java
}

group = "research"
version = "0.1.0"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(17)
    }
}

repositories {
    mavenCentral()
}

// Align with Confluent Platform 8.2 / Apache Kafka 3.8.x
val kafkaVersion = "3.8.0"

dependencies {
    implementation("org.apache.kafka:kafka-streams:$kafkaVersion")
}

application {
    mainClass = "research.kstream.StreamsPipelineApp"
}

tasks.named<JavaCompile>("compileJava") {
    options.encoding = "UTF-8"
}
