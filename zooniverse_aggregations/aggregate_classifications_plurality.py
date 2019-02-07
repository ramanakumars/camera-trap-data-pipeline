""" Aggregate Zooniverse Classifications to obtain
    Labels for Subjects using the Plurality Algorithm
"""
import csv
import os
import argparse
import random
from statistics import median_high
from collections import Counter, defaultdict
import logging

from logger import setup_logger, create_logfile_name
from global_vars import aggregation_flags as flags
from zooniverse_aggregations import aggregator
from utils import print_nested_dict

# args = dict()
# args['classifications_extracted_csv'] = '/home/packerc/shared/zooniverse/Exports/CC/CC_S1_classifications_extracted.csv'
# args['output_csv'] = '/home/packerc/shared/zooniverse/Exports/CC/CC_S1_classifications_aggregated.csv'
# args['subject_csv'] = '/home/packerc/shared/zooniverse/Exports/CC/CC_S1_subjects.csv'
#
# args = dict()
# args['classifications_extracted_csv'] = '/home/packerc/shared/zooniverse/Exports/SER/SER_S1_classifications_extracted.csv'
# args['output_csv'] = '/home/packerc/shared/zooniverse/Exports/SER/SER_S1_classifications_aggregated_v2.csv'
# args['subject_csv'] = None
#
# args = dict()
# args['classifications_extracted_csv'] = '/home/packerc/shared/zooniverse/Exports/GRU/GRU_S1_classifications_extracted.csv'
# args['output_csv'] = '/home/packerc/shared/zooniverse/Exports/GRU/GRU_S1_classifications_aggregated.csv'
# args['subject_csv'] = '/home/packerc/shared/zooniverse/Exports/GRU/GRU_S1_subjects.csv'
#
# args = dict()
# args['classifications_extracted_csv'] = '/home/packerc/shared/zooniverse/Exports/MTZ/MTZ_S1_classifications_extracted.csv'
# args['output_csv'] = '/home/packerc/shared/zooniverse/Exports/MTZ/MTZ_S1_classifications_aggregated.csv'
# args['subject_csv'] = '/home/packerc/shared/zooniverse/Exports/MTZ/MTZ_S1_subjects.csv'

if __name__ == '__main__':

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--classifications_extracted_csv", type=str, required=True,
        help="Path to extracted classifications")
    parser.add_argument(
        "--output_csv", type=str, required=True,
        help="Path to file to store aggregated classifications.")
    parser.add_argument(
        "--export_consensus_only", action="store_true",
        help="Export only species with plurality consensus")
    parser.add_argument(
        "--export_sample_size", default=0, type=int,
        help="Export a csv with N samples (fewer if only consensus)")

    args = vars(parser.parse_args())

    ######################################
    # Check Input
    ######################################

    if not os.path.isfile(args['classifications_extracted_csv']):
        raise FileNotFoundError(
            "classifications_extracted_csv: {} not found".format(
             args['classifications_extracted_csv']))

    ######################################
    # Configuration
    ######################################

    # logging
    log_file_name = create_logfile_name('aggregate_classifications_plurality')
    log_file_path = os.path.join(
        os.path.dirname(args['output_csv']), log_file_name)
    setup_logger(log_file_path)
    logger = logging.getLogger(__name__)

    for k, v in args.items():
        logger.info("Argument {}: {}".format(k, v))

    # logging flags
    print_nested_dict('', flags)

    question_main_id = flags['QUESTION_DELIMITER'].join(
        [flags['QUESTION_PREFIX'], flags['QUESTION_MAIN']])
    question_column_prefix = '{}{}'.format(
        flags['QUESTION_PREFIX'],
        flags['QUESTION_DELIMITER'])

    ######################################
    # Import Classifications
    ######################################

    # Read Annotations and associate with subject id
    subject_annotations = dict()
    with open(args['classifications_extracted_csv'], "r") as ins:
        csv_reader = csv.reader(ins, delimiter=',', quotechar='"')
        header = next(csv_reader)
        row_name_to_id_mapper = {x: i for i, x in enumerate(header)}
        questions = [x for x in header if x.startswith(question_column_prefix)]
        for line_no, line in enumerate(csv_reader):
            # print status
            if ((line_no % 10000) == 0) and (line_no > 0):
                print("Processed {:,} annotations".format(line_no))
            # store data into subject dict
            subject_id = line[row_name_to_id_mapper['subject_id']]
            if subject_id not in subject_annotations:
                subject_annotations[subject_id] = list()
            subject_annotations[subject_id].append(line)

    annotation_id_to_name_mapper = {
        v: k for k, v in row_name_to_id_mapper.items()}

    question_type_map = aggregator.create_question_type_map(
        questions, flags)

    ######################################
    # Aggregate Classifications
    ######################################

    subject_species_aggregations = dict()
    for num, (subject_id, subject_data) in enumerate(subject_annotations.items()):
        # print status
        if ((num % 10000) == 0) and (num > 0):
            print("Aggregated {:,} subjects".format(num))
        # initialize Counter objects
        stat_all = defaultdict(Counter)
        # extract and add annotations to stats counters
        for annotation in subject_data:
            anno_dict = {annotation_id_to_name_mapper[i]: x for
                         i, x in enumerate(annotation)}
            for k, v in anno_dict.items():
                stat_all[k].update({v})
        # extract some stats
        n_species_ids_per_user_median = int(
            median_high(stat_all['user_name'].values()))
        n_subject_classifications = len(stat_all['classification_id'])
        n_subject_users = len(stat_all['user_name'])
        # order species by frequency of annotation
        species_by_frequency = stat_all['question__species'].most_common()
        species_names = [x[0] for x in species_by_frequency]
        # calc stats for the top-species only
        species_stats = aggregator.stats_for_species(
                species_names, subject_data,
                annotation_id_to_name_mapper,
                species_field=question_main_id
                )
        # Aggregate stats for each species
        species_aggs = {x: dict() for x in species_names}
        for species, stats in species_stats.items():
            for question in questions:
                question_type = question_type_map[question]
                if question_type == 'count':
                    agg = aggregator.count_aggregator_median(
                        stats[question], flags)
                elif question_type == 'prop':
                    agg = aggregator.proportion_affirmative(stats[question])
                elif question_type == 'main':
                    continue
                species_aggs[species][question] = agg
            # add overall species stats
            species_aggs[species]['n_users_identified_this_species'] = \
                len(stats['classification_id'])
            n_user_id = species_aggs[species]['n_users_identified_this_species']
            p_user_id = '{:.2f}'.format(n_user_id / n_subject_classifications)
            species_aggs[species]['p_users_identified_this_species'] = p_user_id
        # Determine top / consensus species
        top_species = [
            species_names[i] for i in
            range(n_species_ids_per_user_median)]
        # add info to dict
        agg_info = {'n_species_ids_per_user_median': n_species_ids_per_user_median,
                    'n_users_classified_this_subject': n_subject_users}
        record = {'species_aggregations': species_aggs,
                  'aggregation_info': agg_info,
                  'top_species': top_species}
        subject_species_aggregations[subject_id] = record

    # Create a record per identification
    subject_identificatons = list()
    for subject_id, subject_agg_data in subject_species_aggregations.items():
        # export each species
        for sp, species_dat in subject_agg_data['species_aggregations'].items():
            species_is_plurality_consensus = \
                int(sp in subject_agg_data['top_species'])
            record = {
                question_main_id: sp,
                **species_dat,
                **subject_agg_data['aggregation_info'],
                'species_is_plurality_consensus': species_is_plurality_consensus}
            subject_identificatons.append(record)

    ######################################
    # Generate Stats
    ######################################

    question_stats = defaultdict(Counter)
    question_stats_plurality = defaultdict(Counter)
    subject_stats = dict()
    classifications_per_subject_stats = Counter()
    for _id in subject_identificatons:
        plurality = _id['species_is_plurality_consensus']
        user_classifications = _id['n_users_classified_this_subject']
        subject_id = _id['subject_id']
        for question in questions:
            try:
                if 'count' in question:
                    answer = _id[question]
                else:
                    answer = int(round(float(_id[question]), 0))
            except:
                answer = _id[question]
            if plurality == 1:
                question_stats_plurality[question].update({answer})
            question_stats[question].update({answer})
        subject_stats[subject_id] = user_classifications

    for n_class in subject_stats.values():
        classifications_per_subject_stats.update({n_class})

    # Print Stats per Question - Plurality Consensus Answers Only
    for question, answer_data in question_stats_plurality.items():
        logger.info("Stats for: {} - Plurality Consensus Only".format(question))
        total = sum([x for x in answer_data.values()])
        for answer, count in answer_data.most_common():
            logger.info("Answer: {:20} -- counts: {:10} / {} ({:.2f} %)".format(
                answer, count, total, 100*count/total))

    # Print Stats per Question - All Answers
    for question, answer_data in question_stats_plurality.items():
        logger.info("Stats for: {} - All annotations per subject".format(question))
        total = sum([x for x in answer_data.values()])
        for answer, count in answer_data.most_common():
            logger.info("Answer: {:20} -- counts: {:10} / {} ({:.2f} %)".format(
                answer, count, total, 100*count/total))

    total = sum([x for x in classifications_per_subject_stats.values()])
    for n_classifications, count in classifications_per_subject_stats.items():
        logger.info("Number of Classifications per Subject: {:20} -- counts: {:10} / {} ({:.2f} %)".format(
            n_classifications, count, total, 100*count/total))

    output_header = list(record.keys())

    logger.info("Automatically generated output header: {}".format(
        output_header))

    # Output all Species
    with open(args['output_csv'], 'w') as f:
        csv_writer = csv.writer(f, delimiter=',')
        logger.info("Writing output to {}".format(args['output_csv']))
        csv_writer.writerow(output_header)
        tot = len(subject_identificatons)
        for line_no, record in enumerate(subject_identificatons):
            # skip record if no plurality consensus species
            if args['export_consensus_only']:
                if record['species_is_plurality_consensus'] == '0':
                    continue
            # get subject info data
            to_write = [record[x] for x in output_header]
            csv_writer.writerow(to_write)
            # print status
            if ((line_no % 10000) == 0) and (line_no > 0):
                print("Wrote {:,} identifications".format(line_no))
        logger.info("Wrote {} records to {}".format(
            line_no, args['output_csv']))

    if args['export_sample_size'] > 0:
        # Create a file name for a sampled export
        output_csv_path, output_csv_name = os.path.split(args['output_csv'])
        output_csv_basename = output_csv_name.split('.csv')
        output_csv_sample = os.path.join(
            output_csv_path, output_csv_basename[0] + '_samples.csv')
        # randomly shuffle records
        n_total = len(subject_identificatons)
        _ids_all = [i for i in range(0, n_total)]
        random.seed(123)
        random.shuffle(_ids_all)

        sample_size = min(args['export_sample_size'], n_total)
        _ids_sampled = random.sample(_ids_all, sample_size)

        with open(output_csv_sample, 'w') as f:
            csv_writer = csv.writer(f, delimiter=',')
            logger.info("Writing output to {}".format(output_csv_sample))
            csv_writer.writerow(output_header)
            n_written = 0
            while n_written < sample_size:
                for line_no, line_id in enumerate(_ids_all):
                    record = subject_identificatons[line_id]
                    if args['export_consensus_only']:
                        if record['species_is_plurality_consensus'] == '0':
                            continue
                    # get subject info data
                    to_write = [record[x] for x in output_header]
                    if (line_no % 100) == 0:
                        csv_writer.writerow(to_write)
                    # print status
                    if ((line_no % 10000) == 0) and (line_no > 0):
                        print("Wrote {:,} identifications".format(line_no))
                    n_written += 1
            logger.info("Wrote {} records to {}".format(
                line_no, output_csv_sample))
