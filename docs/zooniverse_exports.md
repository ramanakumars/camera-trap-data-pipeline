# Download and Extract Zooniverse Exports

The following codes can be used to:

1. Get Zooniverse Exports (download data through the Python API)
2. Extract Annotations from Classifications / extract Subjects


For most scripts we use the following ressources (unless indicated otherwise):
```
srun -N 1 --ntasks-per-node=4  --mem-per-cpu=8gb -t 2:00:00 -p interactive --pty bash
module load python3
cd ~/camera-trap-data-pipeline
```

The following examples were run with the following parameters:
```
SITE=GRU
SEASON=GRU_S2
PROJECT_ID=5115
```

## Get Zooniverse Exports

Download Zooniverse exports. Requires Zooniverse account credentials and
collaborator status with the project. The project_id can be found in the project builder
in the top left corner. To create a 'fresh' export it is easiest to go on Zooniverse, to the project page, click on 'Data Exports', and request the appropriate export (see below). After receiving an e-mail confirming the export was completed, execute the following scripts (do not download data via e-mail).

Note: Currently (April 2019) the export contains all historical data from a particular project -- it is only possible to filter by workflow_id.

### Zooniverse Subject Export

To get subject data go to Zooniverse and click 'Request new subject export'. To download the data use:

```
# Get Zooniverse Subject Data
python3 -m zooniverse_exports.get_zooniverse_export \
--password_file ~/keys/passwords.ini \
--project_id $PROJECT_ID \
--output_file /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_subjects.csv \
--export_type subjects \
--log_dir /home/packerc/shared/zooniverse/Exports/${SITE}/log_files/ \
--log_filename ${SEASON}_get_subject_export
```

### Zooniverse Classifications Export

Click on 'Request new classification export' to get the classifications. The structure of a classification is described here: [Zooniverse Classifications](../docs/zooniverse_classification_structure.md).To donwload the classification data from Zooniverse use the following code:

```
python3 -m zooniverse_exports.get_zooniverse_export \
--password_file ~/keys/passwords.ini \
--project_id $PROJECT_ID \
--output_file /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_classifications.csv \
--export_type classifications \
--log_dir /home/packerc/shared/zooniverse/Exports/${SITE}/log_files/ \
--log_filename ${SEASON}_get_classification_export
```

## Extract Zooniverse Subject Data

The following codes extract subject data from the subject exports. The 'filter_by_season' argument selects only subjects from the specified season.

```
python3 -m zooniverse_exports.extract_subjects \
--subject_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_subjects.csv \
--output_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_subjects_extracted.csv \
--filter_by_season ${SEASON} \
--log_dir /home/packerc/shared/zooniverse/Exports/${SITE}/log_files/ \
--log_filename ${SEASON}_extract_subjects
```

The resulting file may have the following column headers:

| Columns   | Description |
| --------- | ----------- |
|capture_id, capture,roll,season,site | internal id's of the capture (uploaded to Zooniverse)
|subject_id | zooniverse unique id of the capture (a subject)
|zooniverse_created_at| Datetime of when the subject was created/uploaded on/to Zooniverse
|zooniverse_retired_at| Datetime of when the subject was retired on Zooniverse (empty if not)
|zooniverse_retirement_reason| Zooniverse system-generated retirement-reason (empty if none / not)
|zooniverse_url_*| Zooniverse URLs to images of the capture / subject


## Extract Zooniverse Annotations from Classifications

The following code extracts the relevant fields of a Zooniverse classification export. It creates a csv file with one line per species identification/annotation. There are several options to select classifications for extractions. Per default only classifications made during the 'live' phase of a project are extracted (this can be overriden). Use only one of the following options to do the extraction.

Use a machine with enough memory - for example:

```
ssh mangi
qsub -I -l walltime=2:00:00,nodes=1:ppn=4,mem=16gb
```

### Option 1) Filter Classifications by Season-ID (Default)

The following script extracts all classifications of a given season, including all workflows and workflow versions. Note that later scripts (i.e. aggregation scripts) may not work if there are multiple workflows. This option requires that the 'season' information was added to the subject's metadata (is default). Inspect the number of classifications that were filtered by 'filter_by_season' for plausibility.

```
python3 -m zooniverse_exports.extract_annotations \
--classification_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_classifications.csv \
--output_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_annotations.csv \
--filter_by_season ${SEASON} \
--log_dir /home/packerc/shared/zooniverse/Exports/${SITE}/log_files/ \
--log_filename ${SEASON}_extract_annotations
```

# Run annotations twice for batches of data processed with integrated AI--first by season, then by workflow ID as below. 
Be sure to specify the workflow and version, and change workflow annotations to annotations_survey.csv.#


### Option 2) Filtering Classifications by Workflow-ID

The workflow_id and the workflow_version can be specified to extract only the workflow the relevant workflow of a project. If neither workflow_id/worfklow_version_min are specified every workflow is extracted. 
The workflow_id can be found in the project builder when clicking on the workflow. The workflow version is at the same place slightly further down (e.g. something like 745.34). 
Be aware that only the 'major' version number is compared against, e.g., workflow version '45.23' is identical to '45.56'. To extract specific workflow versions we can specify a minimum version 'workflow_version_min' in which case all classifications with the same or higher number are extracted. A summary of all extracted workflows and other stats is printed after the extraction.

If WORKFLOW_ID / WORKFLOW_VERSION_MIN are unknown run the script like this:
```
python3 -m zooniverse_exports.extract_annotations \
--classification_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_classifications.csv \
--output_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_annotations.csv

# Alternatively, this information can be found on the extract_annotations.log file within zooniverse/Exports on MSI once the previous script finishes running.# 
```

Then investigate the output of the script in the terminal to determine which workflows to use and then re-run the code with the specified workflows. Example output:
```
INFO:Workflow id: 4655    Workflow version: 4.4        -- counts: 2
INFO:Workflow id: 4655    Workflow version: 173.7      -- counts: 1
INFO:Workflow id: 4655    Workflow version: 209.17     -- counts: 2
INFO:Workflow id: 4655    Workflow version: 226.18     -- counts: 2
INFO:Workflow id: 4655    Workflow version: 303.22     -- counts: 277
INFO:Workflow id: 4655    Workflow version: 304.23     -- counts: 1377468
INFO:Workflow id: 4655    Workflow version: 362.24     -- counts: 405
INFO:Workflow id: 4655    Workflow version: 363.25     -- counts: 842646
```

In that case we would choose 'WORKFLOW_ID=4655' and 'WORKFLOW_VERSION_MIN=304.23' since this seems to be the 'real' start of the season with many annotations. Later changes hopefully were only minor.

WORKFLOW_ID=4979
WORKFLOW_VERSION_MIN=249.2

```

### Extract annotations from workflow only ###
```
python3 -m zooniverse_exports.extract_annotations \
--classification_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_classifications.csv \
--output_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_annotations_survey.csv \
--workflow_id $WORKFLOW_ID \
--workflow_version_min $WORKFLOW_VERSION_MIN \
--log_dir /home/packerc/shared/zooniverse/Exports/${SITE}/log_files/ \
--log_filename ${SEASON}_extract_annotations_survey
```


### Option 3) Filtering Classifications by Date Range

If is is known when the project went live a start-date can be specified such that no classifications made prior to that date are being extracted. There is also the option to specify an end-date: no classification made past that date will be extracted. It is possible to specify only one of the dates. Note: The dates are compared against UTC time.

```
EARLIEST_DATE=2020-11-23
LAST_DATE=2021-04-10
```

```
python3 -m zooniverse_exports.extract_annotations \
--classification_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_classifications.csv \
--output_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_annotations_date.csv \
--no_earlier_than_date $EARLIEST_DATE \
--no_later_than_date $LAST_DATE \
--log_dir /home/packerc/shared/zooniverse/Exports/${SITE}/log_files/ \
--log_filename ${SEASON}_extract_annotations
```

### Option 4) No Filtering

No filtering of any classifications. Usually not recommended.

```
python3 -m zooniverse_exports.extract_annotations \
--classification_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_classifications.csv \
--output_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_annotations.csv \
--log_dir /home/packerc/shared/zooniverse/Exports/${SITE}/log_files/ \
--log_filename ${SEASON}_extract_annotations
```

### Option 5) Combine Filters

All filters can be combined. Example:

```
EARLIEST_DATE=2000-01-01
WORKFLOW_ID=4655
WORKFLOW_VERSION_MIN=304.23
```

```
python3 -m zooniverse_exports.extract_annotations \
--classification_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_classifications.csv \
--output_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_annotations.csv \
--no_earlier_than_date $EARLIEST_DATE \
--workflow_id $WORKFLOW_ID \
--workflow_version_min $WORKFLOW_VERSION_MIN \
--filter_by_season ${SEASON} \
--log_dir /home/packerc/shared/zooniverse/Exports/${SITE}/log_files/ \
--log_filename ${SEASON}_extract_annotations
```


### Other Options

Per default classifications made during the non-live phase of a project are excluded. To include them specify the following parameter.

```
--include_non_live_classifications
```


### Output File


The resulting file may have the following column headers:

| Columns   | Description |
| --------- | ----------- |
|user_name,user_id | user information (user_id null for anonymous users)
|subject_id | zooniverse unique id of the capture (a subject)
|workflow_id,workflow_version | workflow info
|classification_id | classification_id (multiple annotations possible)
|question__(qustion_name)| answer to question (question_name)

One record may look like:

```
user_name,user_id,created_at,subject_id,workflow_id,workflow_version,classification_id,ques
tion__species,question__count,question__standing,question__resting,question__moving,questio
n__eating,question__interacting,question__young_present,question__horns_visible
XYZ,1717856,2018-02-02 06:43:14 UTC,17579137,4986,248.3,88366520,zebra,2,1,0,0,0,0,0,
```

## Filter Annotations with Subject Data (Optional)

To retain only annotations of a specific set of subjects (for example a season) run the following code. This is normally not necessary if a 'filter_by_season' was specified when extracting classifications.

```
python3 -m zooniverse_exports.select_annotations \
--annotations /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_annotations.csv \
--subjects /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_subjects_extracted.csv \
--output_csv /home/packerc/shared/zooniverse/Exports/${SITE}/${SEASON}_annotations.csv \
--log_dir /home/packerc/shared/zooniverse/Exports/${SITE}/log_files/ \
--log_filename ${SEASON}_select_annotations
```

## Processing Snapshot Serengeti S1-S10 data (legacy format)

See [Legacy Extractions](../docs/zooniverse_exports_legacy.md)
